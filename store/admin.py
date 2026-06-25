from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.forms.widgets import ClearableFileInput

from .models import (
    CustomUser, Category, Product, ProductImage, Wishlist,
    Coupon, Address, Order, OrderItem, Cart, CartItem
)

# ------------------------------------------------------------
# Custom form for Category - fully optional image
# ------------------------------------------------------------
class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'
        widgets = {
            'image': ClearableFileInput(attrs={'allow_clear': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make the image field optional
        self.fields['image'].required = False

    def clean_image(self):
        image = self.cleaned_data.get('image')
        # If no file was uploaded (None or an empty file object), return None
        if not image:
            return None
        # Django sometimes passes an InMemoryUploadedFile with empty name
        if hasattr(image, 'name') and not image.name:
            return None
        # Validate the image content
        try:
            from PIL import Image
            img = Image.open(image)
            img.verify()
        except Exception:
            raise forms.ValidationError(
                "Upload a valid image. The file you uploaded was either not an image or a corrupted image."
            )
        return image

# ------------------------------------------------------------
# Custom form for Product (though product has no direct image, kept for consistency)
# ------------------------------------------------------------
class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

# ------------------------------------------------------------
# Inline for Product Images
# ------------------------------------------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'is_primary', 'alt_text', 'image_preview']
    readonly_fields = ['image_preview']
    allow_delete = True
    max_num = 10

    def image_preview(self, obj):
        try:
            if obj.image and hasattr(obj.image, 'url') and obj.image.url:
                return format_html(
                    '<img src="{}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 5px;" />',
                    obj.image.url
                )
        except Exception:
            pass
        return '<span style="color: #999;">No Image</span>'
    image_preview.short_description = 'Preview'

# ------------------------------------------------------------
# Category Admin
# ------------------------------------------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ['name', 'slug', 'parent', 'is_active', 'created_at', 'image_preview']
    list_filter = ['is_active', 'parent', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'image_preview']
    fieldsets = (
        ('Basic Information', {'fields': ('name', 'slug', 'description')}),
        ('Media', {'fields': ('image', 'image_preview')}),
        ('Organization', {'fields': ('parent', 'is_active')}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    def image_preview(self, obj):
        try:
            if obj.image and hasattr(obj.image, 'url') and obj.image.url:
                return format_html(
                    '<img src="{}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 5px;" />',
                    obj.image.url
                )
        except Exception:
            pass
        return '<span style="color: #999;">No Image</span>'
    image_preview.short_description = 'Preview'

# ------------------------------------------------------------
# Product Admin
# ------------------------------------------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ['name', 'category', 'price', 'discount_price', 'stock', 'gender',
                    'is_featured', 'is_active', 'created_at', 'image_preview']
    list_filter = ['category', 'gender', 'is_featured', 'is_active', 'brand', 'created_at']
    search_fields = ['name', 'description', 'brand']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'discount_price', 'stock', 'is_featured', 'is_active']
    readonly_fields = ['views', 'created_at', 'updated_at', 'image_preview']
    inlines = [ProductImageInline]
    fieldsets = (
        ('Basic Information', {'fields': ('name', 'slug', 'description', 'category', 'gender')}),
        ('Pricing', {'fields': ('price', 'discount_price')}),
        ('Inventory', {'fields': ('stock', 'size', 'color')}),
        ('Details', {'fields': ('brand', 'material')}),
        ('Status', {'fields': ('is_featured', 'is_active')}),
        ('Media', {'fields': ('image_preview',), 'description': 'Images can be added in the "Product Images" section below.'}),
        ('Analytics', {'fields': ('views',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def image_preview(self, obj):
        try:
            primary_image = obj.images.filter(is_primary=True).first()
            if primary_image and primary_image.image and hasattr(primary_image.image, 'url'):
                return format_html(
                    '<img src="{}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 5px;" />',
                    primary_image.image.url
                )
            first_image = obj.images.first()
            if first_image and first_image.image and hasattr(first_image.image, 'url'):
                return format_html(
                    '<img src="{}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 5px;" />',
                    first_image.image.url
                )
        except Exception:
            pass
        return '<span style="color: #999;">No Image</span>'
    image_preview.short_description = 'Preview'

# ------------------------------------------------------------
# Custom User Admin
# ------------------------------------------------------------
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'phone', 'city', 'is_active', 'is_staff', 'date_joined', 'profile_image_preview']
    list_filter = ['is_active', 'is_staff', 'city', 'date_joined']
    search_fields = ['username', 'email', 'phone']
    readonly_fields = ['last_login', 'date_joined', 'profile_image_preview']
    fieldsets = (
        ('Personal Information', {'fields': ('username', 'email', 'phone', 'profile_image', 'profile_image_preview')}),
        ('Address', {'fields': ('address_line1', 'address_line2', 'city', 'state', 'pincode')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    def profile_image_preview(self, obj):
        try:
            if obj.profile_image and hasattr(obj.profile_image, 'url') and obj.profile_image.url:
                return format_html(
                    '<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />',
                    obj.profile_image.url
                )
        except Exception:
            pass
        return '<span style="color: #999;">No Image</span>'
    profile_image_preview.short_description = 'Preview'

# ------------------------------------------------------------
# Product Image Admin
# ------------------------------------------------------------
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_primary', 'image_preview', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name', 'alt_text']
    list_editable = ['is_primary']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        try:
            if obj.image and hasattr(obj.image, 'url') and obj.image.url:
                return format_html(
                    '<img src="{}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 5px;" />',
                    obj.image.url
                )
        except Exception:
            pass
        return '<span style="color: #999;">No Image</span>'
    image_preview.short_description = 'Preview'

# ------------------------------------------------------------
# Wishlist, Coupon, Address, Cart, Order, etc. remain unchanged
# (they are already correct)
# ------------------------------------------------------------
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['added_at']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'minimum_amount', 'valid_from', 'valid_to', 'used_count', 'usage_limit', 'is_active']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_to']
    search_fields = ['code']
    list_editable = ['is_active']
    readonly_fields = ['used_count']
    fieldsets = (
        ('Coupon Information', {'fields': ('code', 'discount_type', 'discount_value', 'minimum_amount')}),
        ('Validity', {'fields': ('valid_from', 'valid_to')}),
        ('Usage Limits', {'fields': ('usage_limit', 'used_count')}),
        ('Status', {'fields': ('is_active',)}),
    )

    def save_model(self, request, obj, form, change):
        obj.code = obj.code.upper()
        super().save_model(request, obj, form, change)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'phone', 'city', 'pincode', 'is_default', 'created_at']
    list_filter = ['is_default', 'city', 'state']
    search_fields = ['name', 'phone', 'address_line1', 'city', 'pincode']
    list_editable = ['is_default']
    readonly_fields = ['created_at']

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'size', 'total_price']
    fields = ['product', 'quantity', 'price', 'size', 'total_price']
    can_delete = True
    show_change_link = True

    def total_price(self, obj):
        return f"₹{obj.total_price:,.2f}"
    total_price.short_description = 'Total'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'is_active', 'get_item_count', 'get_total_amount', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__email', 'user__username', 'session_key']
    readonly_fields = ['created_at', 'updated_at', 'get_item_count', 'get_total_amount']
    inlines = [CartItemInline]

    def get_item_count(self, obj):
        return obj.get_item_count()
    get_item_count.short_description = 'Items Count'

    def get_total_amount(self, obj):
        return f"₹{obj.get_total():,.2f}"
    get_total_amount.short_description = 'Total Amount'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'price', 'size', 'total_price', 'created_at']
    list_filter = ['cart__is_active', 'created_at']
    search_fields = ['product__name', 'cart__user__email', 'cart__session_key']
    readonly_fields = ['total_price', 'created_at', 'updated_at']

    def total_price(self, obj):
        return f"₹{obj.total_price:,.2f}"
    total_price.short_description = 'Total'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'size', 'color', 'total_price']
    fields = ['product', 'quantity', 'price', 'size', 'color', 'total_price']
    can_delete = False
    show_change_link = True

    def total_price(self, obj):
        return f"₹{obj.total_price:,.2f}"
    total_price.short_description = 'Total'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'total_amount', 'final_amount', 'status', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['order_id', 'user__email', 'user__username', 'tracking_number']
    readonly_fields = ['order_id', 'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {'fields': ('order_id', 'user', 'address')}),
        ('Payment Details', {'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'payment_status')}),
        ('Amount Details', {'fields': ('total_amount', 'discount_amount', 'coupon', 'final_amount')}),
        ('Status', {'fields': ('status', 'tracking_number', 'order_note')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    actions = ['mark_as_pending', 'mark_as_processing', 'mark_as_confirmed', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']

    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')
        self.message_user(request, f"{queryset.count()} order(s) marked as Pending.")
    mark_as_pending.short_description = "Mark selected orders as Pending"

    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, f"{queryset.count()} order(s) marked as Processing.")
    mark_as_processing.short_description = "Mark selected orders as Processing"

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f"{queryset.count()} order(s) marked as Confirmed.")
    mark_as_confirmed.short_description = "Mark selected orders as Confirmed"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, f"{queryset.count()} order(s) marked as Shipped.")
    mark_as_shipped.short_description = "Mark selected orders as Shipped"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, f"{queryset.count()} order(s) marked as Delivered.")
    mark_as_delivered.short_description = "Mark selected orders as Delivered"

    def mark_as_cancelled(self, request, queryset):
        for order in queryset:
            if order.status in ['pending', 'confirmed', 'processing']:
                order.status = 'cancelled'
                order.save()
                for item in order.items.all():
                    product = item.product
                    product.stock += item.quantity
                    product.save()
        self.message_user(request, f"{queryset.count()} order(s) marked as Cancelled.")
    mark_as_cancelled.short_description = "Mark selected orders as Cancelled"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'total_price']
    list_filter = ['order__status']
    search_fields = ['order__order_id', 'product__name']
    readonly_fields = ['order', 'product', 'quantity', 'price', 'size', 'color']

    def total_price(self, obj):
        return f"₹{obj.total_price:,.2f}"
    total_price.short_description = 'Total'

# Custom Admin Site Configuration
admin.site.site_header = 'Fashion E-Commerce Administration'
admin.site.site_title = 'Fashion E-Commerce Admin Portal'
admin.site.index_title = 'Welcome to Fashion E-Commerce Admin Dashboard'