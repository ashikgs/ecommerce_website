import random
import string
import razorpay
from io import BytesIO
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.sessions.models import Session
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.contrib.auth import get_user_model
from .models import Cart, CartItem, Order, OrderItem, Address, Coupon
from .forms import AddressForm, CouponForm
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cart, CartItem, Order, OrderItem, Address, Coupon
from .forms import AddressForm, CouponForm


from .models import (
    Category, Product, ProductImage, Wishlist, Cart, CartItem,
    Coupon, Address, Order, OrderItem
)
from .forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm,
    AddressForm, CouponForm
)

# ---------- SAFE USER RETRIEVAL ----------
User = get_user_model()

def get_safe_user(request):
    """Returns a User instance or None – never a string."""
    if not request.user.is_authenticated:
        return None
    if isinstance(request.user, User):
        return request.user
    # Fallback: try to retrieve from session
    try:
        session_key = request.session.session_key
        if session_key:
            session = Session.objects.get(session_key=session_key)
            user_id = session.get_decoded().get('_auth_user_id')
            if user_id:
                if isinstance(user_id, str):
                    return User.objects.get(username=user_id)
                else:
                    return User.objects.get(pk=user_id)
    except Exception:
        pass
    return None
# ---------- Safe cart helper ----------
def get_or_create_cart(request):
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key, is_active=True)
    return cart
# ---------- Home & Product ----------
def home(request):
    featured_products = Product.objects.filter(is_featured=True, is_active=True)[:12]
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:12]
    categories = Category.objects.filter(parent=None, is_active=True)[:8]
    return render(request, 'home.html', {
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'categories': categories,
    })

def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query)
        )
    gender = request.GET.get('gender')
    if gender:
        products = products.filter(gender=gender)
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    sort_by = request.GET.get('sort_by')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'popular':
        products = products.order_by('-views')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Get user's wishlist item IDs
    real_user = get_safe_user(request)
    wishlist_product_ids = []
    if real_user:
        wishlist_product_ids = list(Wishlist.objects.filter(user=real_user).values_list('product_id', flat=True))

    return render(request, 'product_list.html', {
        'products': page_obj,
        'categories': categories,
        'search_query': search_query,
        'gender': gender,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'wishlist_product_ids': wishlist_product_ids,
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    product.views += 1
    product.save()
    related_products = Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)[:8]
    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products,
    })

# ---------- Cart ----------
def add_to_cart(request, product_id):
    # Log out if user is a string (just for cleanliness)
    if request.user.is_authenticated and not isinstance(request.user, get_user_model()):
        logout(request)

    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, is_active=True)
        cart = get_or_create_cart(request)
        quantity = int(request.POST.get('quantity', 1))
        size = request.POST.get('size', '')

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            size=size,
            defaults={'quantity': quantity, 'price': product.final_price}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        if request.GET.get('ajax') == '1' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': cart.get_item_count(),
                'message': f'{product.name} added to cart!'
            })

        messages.success(request, f'{product.name} added to cart!')
    return redirect('store:cart_view')

def cart_view(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    subtotal = sum(item.total_price for item in cart_items)

    discount = 0
    if request.session.get('coupon_code'):
        try:
            coupon = Coupon.objects.get(code=request.session['coupon_code'])
            if coupon.is_valid():
                if coupon.discount_type == 'percentage':
                    discount = (subtotal * coupon.discount_value) / 100
                else:
                    discount = coupon.discount_value
                discount = min(discount, subtotal)
        except Coupon.DoesNotExist:
            del request.session['coupon_code']

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'total': subtotal - discount,
        'coupon_form': CouponForm(),
    })

def get_cart_totals_dict(request, cart):
    subtotal = cart.get_total()
    discount = 0
    if request.session.get('coupon_code'):
        try:
            coupon = Coupon.objects.get(code=request.session['coupon_code'])
            if coupon.is_valid():
                if coupon.discount_type == 'percentage':
                    discount = (subtotal * coupon.discount_value) / 100
                else:
                    discount = coupon.discount_value
                discount = min(discount, subtotal)
        except Coupon.DoesNotExist:
            del request.session['coupon_code']
    total = subtotal - discount
    return {
        'subtotal': float(subtotal),
        'discount': float(discount),
        'total': float(total),
        'cart_count': cart.get_item_count()
    }

@require_POST
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart = get_or_create_cart(request)
    if cart_item.cart != cart:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    quantity = int(request.POST.get('quantity', 1))
    if 0 < quantity <= cart_item.product.stock:
        cart_item.quantity = quantity
        cart_item.save()
        totals = get_cart_totals_dict(request, cart)
        return JsonResponse({
            'success': True,
            'item_total': float(cart_item.total_price),
            **totals
        })
    return JsonResponse({'success': False, 'error': 'Invalid quantity or out of stock'})

@require_POST
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart = get_or_create_cart(request)
    if cart_item.cart == cart:
        cart_item.delete()
        totals = get_cart_totals_dict(request, cart)
        return JsonResponse({
            'success': True,
            **totals
        })
    return JsonResponse({'success': False, 'error': 'Unauthorized'})


# ---------- Wishlist ----------

def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product')

    return render(
        request,
        'wishlist.html',
        {'wishlist_items': wishlist_items}
    )

def add_to_wishlist(request, product_id):
    user = get_safe_user(request)
    if not user:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)
    product = get_object_or_404(Product, id=product_id)
    obj, created = Wishlist.objects.get_or_create(user=user, product=product)
    wishlist_count = Wishlist.objects.filter(user=user).count()
    return JsonResponse({
        'success': True,
        'created': created,
        'wishlist_count': wishlist_count,
        'message': 'Added to wishlist!' if created else 'Already in wishlist!'
    })

def remove_from_wishlist(request, product_id):
    user = get_safe_user(request)
    if not user:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=user, product=product).delete()
    wishlist_count = Wishlist.objects.filter(user=user).count()
    return JsonResponse({'success': True, 'wishlist_count': wishlist_count})

# ---------- Coupon ----------
@require_POST
def apply_coupon(request):
    form = CouponForm(request.POST)
    if form.is_valid():
        code = form.cleaned_data['code']
        try:
            coupon = Coupon.objects.get(code=code)
            if coupon.is_valid():
                request.session['coupon_code'] = code
                messages.success(request, 'Coupon applied successfully!')
            else:
                messages.error(request, 'Coupon is invalid or expired!')
        except Coupon.DoesNotExist:
            messages.error(request, 'Invalid coupon code!')
    return redirect('store:cart_view')

def remove_coupon(request):
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
        messages.success(request, 'Coupon removed!')
    return redirect('store:cart_view')

# ---------- Checkout & Payment ----------

User = get_user_model()

def checkout(request):
    # ---------- STEP 1: Convert string user to real User ----------
    real_user = None
    if request.user.is_authenticated:
        if isinstance(request.user, User):
            real_user = request.user
        else:
            # request.user is a string (e.g. 'ashik') → look up by username
            try:
                real_user = User.objects.get(username=str(request.user))
            except User.DoesNotExist:
                pass
    if not real_user:
        return redirect('store:login')

    # ---------- STEP 2: Cart using session key only (no user) ----------
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key, is_active=True)

    cart_items = cart.items.all()
    if not cart_items:
        messages.warning(request, 'Your cart is empty!')
        return redirect('store:cart_view')

    subtotal = cart.get_total()
    discount = 0
    if request.session.get('coupon_code'):
        try:
            coupon = Coupon.objects.get(code=request.session['coupon_code'])
            if coupon.is_valid():
                if coupon.discount_type == 'percentage':
                    discount = (subtotal * coupon.discount_value) / 100
                else:
                    discount = coupon.discount_value
                discount = min(discount, subtotal)
        except Coupon.DoesNotExist:
            del request.session['coupon_code']
    total = subtotal - discount

    # Now use real_user in all filters
    addresses = Address.objects.filter(user=real_user)
    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        if address_id:
            address = get_object_or_404(Address, id=address_id, user=real_user)
        else:
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = real_user
                address.save()
            else:
                return render(request, 'checkout.html', {
                    'cart_items': cart_items,
                    'subtotal': subtotal,
                    'discount': discount,
                    'total': total,
                    'addresses': addresses,
                    'default_address': default_address,
                    'address_form': address_form,
                })

        order = Order.objects.create(
            user=real_user,
            address=address,
            total_amount=subtotal,
            discount_amount=discount,
            final_amount=total,
            status='pending',
            payment_status='pending'
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.price,
                size=item.size,
                color=item.color
            )
        cart.is_active = False
        cart.save()

        if 'coupon_code' in request.session:
            coupon = Coupon.objects.get(code=request.session['coupon_code'])
            coupon.used_count += 1
            coupon.save()
            order.coupon = coupon
            order.save()
            del request.session['coupon_code']

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            'amount': int(total * 100),
            'currency': 'INR',
            'payment_capture': '1',
            'receipt': order.order_id
        })
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        return render(request, 'payment.html', {
            'order': order,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': total,
            'user': real_user,
        })

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'total': total,
        'addresses': addresses,
        'default_address': default_address,
        'address_form': AddressForm(),
    })
def payment_success(request):
    order_id = request.GET.get('order_id')
    payment_id = request.GET.get('payment_id')
    signature = request.GET.get('signature')
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    order = get_object_or_404(Order, order_id=order_id, user=user)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    params_dict = {
        'razorpay_order_id': order.razorpay_order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        order.payment_status = 'completed'
        order.status = 'confirmed'
        order.razorpay_payment_id = payment_id
        order.razorpay_signature = signature
        order.save()
        for item in order.items.all():
            product = item.product
            product.stock -= item.quantity
            product.save()
        messages.success(request, 'Payment successful! Your order has been placed.')
        return redirect('store:order_detail', order_id=order.order_id)
    except Exception:
        order.payment_status = 'failed'
        order.save()
        messages.error(request, 'Payment verification failed!')
        return redirect('store:order_detail', order_id=order.order_id)

def payment_failed(request):
    order_id = request.GET.get('order_id')
    if order_id:
        user = get_safe_user(request)
        if user:
            order = get_object_or_404(Order, order_id=order_id, user=user)
            order.payment_status = 'failed'
            order.save()
    messages.error(request, 'Payment failed. Please try again.')
    return redirect('store:cart_view')

# ---------- Orders ----------
def my_orders(request):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    orders = Order.objects.filter(user=user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})

def order_detail(request, order_id):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    order = get_object_or_404(Order, order_id=order_id, user=user)
    return render(request, 'order_detail.html', {'order': order})

def cancel_order(request, order_id):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    order = get_object_or_404(Order, order_id=order_id, user=user)
    if order.status in ['pending', 'confirmed', 'processing']:
        order.status = 'cancelled'
        order.save()
        for item in order.items.all():
            item.product.stock += item.quantity
            item.product.save()
        messages.success(request, 'Order cancelled successfully!')
    else:
        messages.error(request, 'This order cannot be cancelled!')
    return redirect('store:order_detail', order_id=order.order_id)

def track_order(request, order_id):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    order = get_object_or_404(Order, order_id=order_id, user=user)
    return render(request, 'track_order.html', {'order': order})

def download_invoice(request, order_id):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    order = get_object_or_404(Order, order_id=order_id, user=user)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#333333'), spaceAfter=30)
    elements.append(Paragraph(f"Invoice #{order.order_id}", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%B %d, %Y')}", styles['Normal']))
    elements.append(Paragraph(f"Status: {order.get_status_display()}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Customer Information", styles['Heading2']))
    elements.append(Paragraph(f"Name: {order.address.name}", styles['Normal']))
    elements.append(Paragraph(f"Phone: {order.address.phone}", styles['Normal']))
    elements.append(Paragraph(f"Address: {order.address.address_line1}", styles['Normal']))
    if order.address.address_line2:
        elements.append(Paragraph(f"{order.address.address_line2}", styles['Normal']))
    elements.append(Paragraph(f"{order.address.city}, {order.address.state} - {order.address.pincode}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Order Items", styles['Heading2']))
    table_data = [['Product', 'Size', 'Quantity', 'Price', 'Total']]
    for item in order.items.all():
        table_data.append([item.product.name, item.size or '-', str(item.quantity), f"₹{item.price}", f"₹{item.total_price}"])
    table_data.append(['', '', '', 'Subtotal:', f"₹{order.total_amount}"])
    if order.discount_amount > 0:
        table_data.append(['', '', '', 'Discount:', f"-₹{order.discount_amount}"])
    table_data.append(['', '', '', 'Total:', f"₹{order.final_amount}"])
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (3, len(table_data)-3), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
    return response

# ---------- Authentication ----------
def register(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please login below.')
            return redirect('store:login')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('store:main')
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Merge guest cart
                session_key = request.session.session_key
                if session_key:
                    guest_cart = Cart.objects.filter(session_key=session_key, is_active=True).first()
                    if guest_cart:
                        user_cart, _ = Cart.objects.get_or_create(user=user, is_active=True)
                        for item in guest_cart.items.all():
                            cart_item, created = CartItem.objects.get_or_create(
                                cart=user_cart, product=item.product, size=item.size,
                                defaults={'quantity': item.quantity, 'price': item.price}
                            )
                            if not created:
                                cart_item.quantity += item.quantity
                                cart_item.save()
                        guest_cart.is_active = False
                        guest_cart.save()
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next', 'store:main')
                return redirect(next_url)
        messages.error(request, 'Invalid username or password!')
    else:
        form = UserLoginForm()
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('store:home')

# ---------- Profile & Address ----------
def profile(request):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    return render(request, 'profile.html', {'user': user})

def edit_profile(request):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('store:profile')
    else:
        form = UserProfileForm(instance=user)
    return render(request, 'edit_profile.html', {'form': form})

def address_list(request):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    addresses = Address.objects.filter(user=user)
    return render(request, 'address_list.html', {'addresses': addresses})

def add_address(request):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = user
            address.save()
            messages.success(request, 'Address added successfully!')
            return redirect('store:address_list')
    else:
        form = AddressForm()
    return render(request, 'add_address.html', {'form': form})

def edit_address(request, address_id):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    address = get_object_or_404(Address, id=address_id, user=user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('store:address_list')
    else:
        form = AddressForm(instance=address)
    return render(request, 'edit_address.html', {'form': form, 'address': address})

def delete_address(request, address_id):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    address = get_object_or_404(Address, id=address_id, user=user)
    address.delete()
    messages.success(request, 'Address deleted successfully!')
    return redirect('store:address_list')

def set_default_address(request, address_id):
    user = get_safe_user(request)
    if not user:
        return redirect('store:login')
    address = get_object_or_404(Address, id=address_id, user=user)
    Address.objects.filter(user=user).update(is_default=False)
    address.is_default = True
    address.save()
    messages.success(request, 'Default address set successfully!')
    return redirect('store:address_list')

# ---------- Search ----------
def search_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(Q(name__icontains=query) | Q(brand__icontains=query), is_active=True)[:10]
        results = [{'name': p.name, 'slug': p.slug} for p in products]
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})

def main_view(request):
    real_user = get_safe_user(request)
    if not real_user:
        return redirect('store:login')
    
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(parent=None, is_active=True)
    
    # Apply search query
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query)
        )
        
    # Apply category query
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
        
    # Get user's wishlist item IDs
    wishlist_product_ids = []
    if real_user:
        wishlist_product_ids = list(Wishlist.objects.filter(user=real_user).values_list('product_id', flat=True))
        
    return render(request, 'main.html', {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'category_slug': category_slug,
        'wishlist_product_ids': wishlist_product_ids,
    })

def checkout_single(request, product_id):
    real_user = get_safe_user(request)
    if not real_user:
        return redirect('store:login')
        
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Retrieve parameters
    quantity = int(request.GET.get('quantity', 1) if request.method == 'GET' else request.POST.get('quantity', 1))
    size = request.GET.get('size', '') if request.method == 'GET' else request.POST.get('size', '')
    color = request.GET.get('color', '') if request.method == 'GET' else request.POST.get('color', '')
    
    subtotal = product.final_price * quantity
    discount = 0
    
    # Handle coupon if any
    coupon_discount_type = ""
    coupon_discount_value = 0
    if request.session.get('coupon_code'):
        try:
            coupon = Coupon.objects.get(code=request.session['coupon_code'])
            if coupon.is_valid():
                coupon_discount_type = coupon.discount_type
                coupon_discount_value = float(coupon.discount_value)
                if coupon.discount_type == 'percentage':
                    discount = (subtotal * coupon.discount_value) / 100
                else:
                    discount = coupon.discount_value
                discount = min(discount, subtotal)
        except Coupon.DoesNotExist:
            del request.session['coupon_code']
    total = subtotal - discount
    
    addresses = Address.objects.filter(user=real_user)
    default_address = addresses.filter(is_default=True).first()
    
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        if address_id:
            address = get_object_or_404(Address, id=address_id, user=real_user)
        else:
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = real_user
                address.save()
            else:
                return render(request, 'checkout_single.html', {
                    'product': product,
                    'quantity': quantity,
                    'size': size,
                    'color': color,
                    'subtotal': subtotal,
                    'discount': discount,
                    'total': total,
                    'addresses': addresses,
                    'default_address': default_address,
                    'address_form': address_form,
                    'coupon_discount_type': coupon_discount_type,
                    'coupon_discount_value': coupon_discount_value,
                })
                
        order = Order.objects.create(
            user=real_user,
            address=address,
            total_amount=subtotal,
            discount_amount=discount,
            final_amount=total,
            status='pending',
            payment_status='pending'
        )
        
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.final_price,
            size=size,
            color=color
        )
        
        if 'coupon_code' in request.session:
            coupon = Coupon.objects.get(code=request.session['coupon_code'])
            coupon.used_count += 1
            coupon.save()
            order.coupon = coupon
            order.save()
            del request.session['coupon_code']
            
        # Razorpay payment Integration
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            'amount': int(total * 100),
            'currency': 'INR',
            'payment_capture': '1',
            'receipt': order.order_id
        })
        order.razorpay_order_id = razorpay_order['id']
        order.save()
        
        return render(request, 'payment.html', {
            'order': order,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': total,
            'user': real_user,
        })
        
    return render(request, 'checkout_single.html', {
        'product': product,
        'quantity': quantity,
        'size': size,
        'color': color,
        'subtotal': subtotal,
        'discount': discount,
        'total': total,
        'addresses': addresses,
        'default_address': default_address,
        'address_form': AddressForm(),
        'coupon_discount_type': coupon_discount_type,
        'coupon_discount_value': coupon_discount_value,
    })

