from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Home and Products
    path('', views.home, name='home'),
    path('shop/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    
    # Cart
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    
    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    
    # Coupons
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
    path('coupon/remove/', views.remove_coupon, name='remove_coupon'),
    
    # Checkout & Payment
    path('checkout/', views.checkout, name='checkout'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    
    # Orders
    path('orders/', views.my_orders, name='my_orders'),
    path('order/<str:order_id>/', views.order_detail, name='order_detail'),
    path('order/<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<str:order_id>/track/', views.track_order, name='track_order'),
    path('order/<str:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Addresses
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/add/', views.add_address, name='add_address'),
    path('addresses/<int:address_id>/edit/', views.edit_address, name='edit_address'),
    path('addresses/<int:address_id>/delete/', views.delete_address, name='delete_address'),
    path('addresses/<int:address_id>/default/', views.set_default_address, name='set_default_address'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Main Page
    path('main/', views.main_view, name='main'),
    
    # Single Item Checkout
    path('checkout/single/<int:product_id>/', views.checkout_single, name='checkout_single'),
    
    # Search
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
]