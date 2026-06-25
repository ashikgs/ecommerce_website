from .models import Cart, Wishlist

def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_active=True).first()
        if cart:
            count = cart.get_item_count()
    elif request.session.session_key:
        cart = Cart.objects.filter(session_key=request.session.session_key, is_active=True).first()
        if cart:
            count = cart.get_item_count()
    return {'cart_count': count}

def wishlist_count(request):
    count = 0
    if request.user.is_authenticated:
        count = Wishlist.objects.filter(user=request.user).count()
    return {'wishlist_count': count}