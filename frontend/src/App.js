import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ---- Context ----
const AppContext = createContext();
export const useApp = () => useContext(AppContext);

function AppProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('bk2_token'));
  const [user, setUser] = useState(null);
  const [cart, setCart] = useState([]);
  const [categories, setCategories] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);

  const authHeader = token ? `Bearer ${token}` : '';

  const fetchUser = useCallback(async () => {
    if (!token) return;
    try {
      const r = await fetch(`${API_URL}/api/auth/me?authorization=${encodeURIComponent(authHeader)}`);
      if (r.ok) setUser(await r.json());
      else { localStorage.removeItem('bk2_token'); setToken(null); }
    } catch(e) {}
  }, [token, authHeader]);

  const fetchCategories = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/categories`);
      if (r.ok) { const d = await r.json(); setCategories(d.data); }
    } catch(e) {}
  }, []);

  const fetchCart = useCallback(async () => {
    if (!token) { setCart([]); return; }
    try {
      const r = await fetch(`${API_URL}/api/cart?authorization=${encodeURIComponent(authHeader)}`);
      if (r.ok) { const d = await r.json(); setCart(d.data); }
    } catch(e) {}
  }, [token, authHeader]);

  const addToCart = async (productId) => {
    if (!token) return;
    await fetch(`${API_URL}/api/cart/add?authorization=${encodeURIComponent(authHeader)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId }),
    });
    fetchCart();
  };

  const updateCart = async (cartItemId, qty) => {
    await fetch(`${API_URL}/api/cart/update?authorization=${encodeURIComponent(authHeader)}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cart_item_id: cartItemId, quantity: qty }),
    });
    fetchCart();
  };

  const removeFromCart = async (cartItemId) => {
    await fetch(`${API_URL}/api/cart/remove?authorization=${encodeURIComponent(authHeader)}`, {
      method: 'DELETE', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cart_item_id: cartItemId }),
    });
    fetchCart();
  };

  const login = (t, u) => { localStorage.setItem('bk2_token', t); setToken(t); setUser(u); };
  const logout = () => { localStorage.removeItem('bk2_token'); setToken(null); setUser(null); setCart([]); };

  const totalQty = cart.reduce((s, c) => s + c.quantity, 0);
  const totalPrice = cart.reduce((s, c) => {
    const p = c.product;
    const price = p.discount ? Math.round(p.price * (1 - p.discount / 100)) : p.price;
    return s + price * c.quantity;
  }, 0);

  useEffect(() => { fetchUser(); }, [fetchUser]);
  useEffect(() => { fetchCategories(); }, [fetchCategories]);
  useEffect(() => { fetchCart(); }, [fetchCart]);

  return (
    <AppContext.Provider value={{ token, user, cart, categories, cartOpen, setCartOpen, addToCart, updateCart, removeFromCart, login, logout, totalQty, totalPrice, authHeader, fetchCart }}>
      {children}
    </AppContext.Provider>
  );
}

// ---- Price Helpers ----
function formatPrice(p) { return `₹${p}`; }
function discountedPrice(price, discount) { return discount ? Math.round(price * (1 - discount / 100)) : price; }

// ---- Header ----
function Header() {
  const { user, totalQty, totalPrice, setCartOpen, logout } = useApp();
  const [search, setSearch] = useState('');
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleSearch = (e) => {
    e.preventDefault();
    if (search.trim()) { navigate(`/search?q=${encodeURIComponent(search.trim())}`); }
  };

  return (
    <header className="bk-header" data-testid="header">
      <div className="bk-header-inner">
        <Link to="/" className="bk-logo" data-testid="logo-link">
          <div className="bk-logo-icon">B</div>
          <div className="bk-logo-text">
            <span className="bk-logo-name">blinkit2</span>
            <span className="bk-logo-tag">in 10 minutes</span>
          </div>
        </Link>

        <form className="bk-search" onSubmit={handleSearch} data-testid="search-form">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input type="text" placeholder="Search for products..." value={search} onChange={e => setSearch(e.target.value)} data-testid="search-input" />
        </form>

        <div className="bk-header-right">
          {user ? (
            <div className="bk-user-menu" data-testid="user-menu">
              <button className="bk-user-btn" onClick={() => setMenuOpen(!menuOpen)} data-testid="account-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <span>{user.name?.split(' ')[0]}</span>
              </button>
              {menuOpen && (
                <div className="bk-dropdown" data-testid="user-dropdown">
                  <Link to="/orders" className="bk-dropdown-item" onClick={() => setMenuOpen(false)} data-testid="my-orders-link">My Orders</Link>
                  <button className="bk-dropdown-item" onClick={() => { setMenuOpen(false); logout(); }} data-testid="logout-btn">Logout</button>
                </div>
              )}
            </div>
          ) : (
            <Link to="/login" className="bk-login-btn" data-testid="login-link">Login</Link>
          )}

          <button className="bk-cart-btn" onClick={() => setCartOpen(true)} data-testid="cart-btn">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
            {totalQty > 0 ? (
              <div className="bk-cart-info">
                <span>{totalQty} items</span>
                <span>{formatPrice(totalPrice)}</span>
              </div>
            ) : (
              <span>My Cart</span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}

// ---- Cart Sidebar ----
function CartSidebar() {
  const { cart, cartOpen, setCartOpen, updateCart, removeFromCart, totalPrice, totalQty } = useApp();
  const navigate = useNavigate();

  if (!cartOpen) return null;

  const deliveryFee = totalPrice >= 199 ? 0 : 25;

  return (
    <>
      <div className="bk-overlay" onClick={() => setCartOpen(false)} />
      <div className="bk-cart-sidebar" data-testid="cart-sidebar">
        <div className="bk-cart-header">
          <h3>My Cart</h3>
          <button onClick={() => setCartOpen(false)} data-testid="close-cart-btn">&times;</button>
        </div>

        {cart.length === 0 ? (
          <div className="bk-cart-empty">
            <p>Your cart is empty</p>
            <button onClick={() => setCartOpen(false)} className="bk-btn-primary">Start Shopping</button>
          </div>
        ) : (
          <>
            <div className="bk-delivery-badge">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0C831F" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
              <span>Delivery in <strong>10 minutes</strong></span>
            </div>

            <div className="bk-cart-items">
              {cart.map(item => {
                const p = item.product;
                const price = discountedPrice(p.price, p.discount);
                return (
                  <div key={item.cart_item_id} className="bk-cart-item" data-testid={`cart-item-${item.cart_item_id}`}>
                    <img src={p.image} alt={p.name} onError={e => { e.target.src = 'https://via.placeholder.com/80?text=Product'; }} />
                    <div className="bk-cart-item-info">
                      <p className="bk-cart-item-name">{p.name}</p>
                      <p className="bk-cart-item-unit">{p.unit}</p>
                      <p className="bk-cart-item-price">{formatPrice(price)}</p>
                    </div>
                    <div className="bk-qty-control">
                      <button onClick={() => updateCart(item.cart_item_id, item.quantity - 1)} data-testid={`qty-minus-${item.cart_item_id}`}>-</button>
                      <span>{item.quantity}</span>
                      <button onClick={() => updateCart(item.cart_item_id, item.quantity + 1)} data-testid={`qty-plus-${item.cart_item_id}`}>+</button>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="bk-cart-bill">
              <h4>Bill details</h4>
              <div className="bk-bill-row"><span>Items total</span><span>{formatPrice(totalPrice)}</span></div>
              <div className="bk-bill-row"><span>Delivery charge</span><span>{deliveryFee === 0 ? <span className="bk-free">FREE</span> : formatPrice(deliveryFee)}</span></div>
              <div className="bk-bill-row bk-bill-total"><span>Grand total</span><span>{formatPrice(totalPrice + deliveryFee)}</span></div>
            </div>

            <div className="bk-cart-footer">
              <div className="bk-cart-footer-total">
                <span>{formatPrice(totalPrice + deliveryFee)}</span>
                <span className="bk-cart-footer-label">TOTAL</span>
              </div>
              <button className="bk-checkout-btn" onClick={() => { setCartOpen(false); navigate('/checkout'); }} data-testid="proceed-checkout-btn">
                Proceed to Checkout
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}

// ---- Product Card ----
function ProductCard({ product }) {
  const { addToCart, cart, updateCart, token } = useApp();
  const navigate = useNavigate();
  const price = discountedPrice(product.price, product.discount);
  const cartItem = cart.find(c => c.product_id === product.product_id);

  const handleAdd = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!token) { navigate('/login'); return; }
    addToCart(product.product_id);
  };

  return (
    <div className="bk-product-card" data-testid={`product-card-${product.product_id}`} onClick={() => navigate(`/product/${product.product_id}`)}>
      <div className="bk-product-img-wrap">
        <img src={product.image} alt={product.name} onError={e => { e.target.src = 'https://via.placeholder.com/200?text=Product'; }} />
        {product.discount > 0 && <span className="bk-discount-tag">{product.discount}% OFF</span>}
      </div>
      <div className="bk-delivery-time">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#0C831F" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
        <span>10 MINS</span>
      </div>
      <p className="bk-product-name">{product.name}</p>
      <p className="bk-product-unit">{product.unit}</p>
      <div className="bk-product-bottom">
        <div className="bk-product-prices">
          <span className="bk-price-now">{formatPrice(price)}</span>
          {product.discount > 0 && <span className="bk-price-old">{formatPrice(product.price)}</span>}
        </div>
        {product.stock === 0 ? (
          <span className="bk-out-of-stock">Out of stock</span>
        ) : cartItem ? (
          <div className="bk-qty-control bk-qty-sm" onClick={e => e.stopPropagation()}>
            <button onClick={(e) => { e.stopPropagation(); updateCart(cartItem.cart_item_id, cartItem.quantity - 1); }}>-</button>
            <span>{cartItem.quantity}</span>
            <button onClick={(e) => { e.stopPropagation(); updateCart(cartItem.cart_item_id, cartItem.quantity + 1); }}>+</button>
          </div>
        ) : (
          <button className="bk-add-btn" onClick={handleAdd} data-testid={`add-to-cart-${product.product_id}`}>ADD</button>
        )}
      </div>
    </div>
  );
}

// ---- Category Row ----
function CategoryProducts({ categoryId, categoryName }) {
  const [products, setProducts] = useState([]);
  const scrollRef = React.useRef();

  useEffect(() => {
    fetch(`${API_URL}/api/products/category/${categoryId}`)
      .then(r => r.json())
      .then(d => setProducts(d.data))
      .catch(() => {});
  }, [categoryId]);

  if (products.length === 0) return null;

  return (
    <div className="bk-cat-section" data-testid={`category-section-${categoryId}`}>
      <div className="bk-cat-section-header">
        <h3>{categoryName}</h3>
        <Link to={`/category/${categoryId}`} className="bk-see-all">see all</Link>
      </div>
      <div className="bk-cat-scroll" ref={scrollRef}>
        {products.map(p => <ProductCard key={p.product_id} product={p} />)}
      </div>
    </div>
  );
}

// ---- Home Page ----
function HomePage() {
  const { categories } = useApp();

  return (
    <div className="bk-home" data-testid="home-page">
      <div className="bk-banner">
        <div className="bk-banner-content">
          <h1>Groceries delivered in <span className="bk-highlight">10 minutes</span></h1>
          <p>Get your daily essentials delivered to your doorstep in minutes</p>
        </div>
        <div className="bk-banner-visual">
          <div className="bk-timer-badge">
            <span className="bk-timer-num">10</span>
            <span className="bk-timer-label">minutes</span>
          </div>
        </div>
      </div>

      <div className="bk-categories-grid" data-testid="categories-grid">
        {categories.map(cat => (
          <Link to={`/category/${cat.category_id}`} key={cat.category_id} className="bk-category-card" data-testid={`category-card-${cat.category_id}`}>
            <img src={cat.image} alt={cat.name} onError={e => { e.target.src = 'https://via.placeholder.com/120?text=Category'; }} />
            <span>{cat.name}</span>
          </Link>
        ))}
      </div>

      {categories.map(cat => (
        <CategoryProducts key={cat.category_id} categoryId={cat.category_id} categoryName={cat.name} />
      ))}
    </div>
  );
}

// ---- Category Page ----
function CategoryPage() {
  const { id } = useParams();
  const { categories } = useApp();
  const [products, setProducts] = useState([]);
  const cat = categories.find(c => c.category_id === id);

  useEffect(() => {
    fetch(`${API_URL}/api/products?category_id=${id}&limit=50`)
      .then(r => r.json())
      .then(d => setProducts(d.data))
      .catch(() => {});
  }, [id]);

  return (
    <div className="bk-page" data-testid="category-page">
      <h2 className="bk-page-title">{cat?.name || 'Category'}</h2>
      <div className="bk-products-grid">
        {products.map(p => <ProductCard key={p.product_id} product={p} />)}
        {products.length === 0 && <p className="bk-no-data">No products found</p>}
      </div>
    </div>
  );
}

// ---- Search Page ----
function SearchPage() {
  const [params] = useSearchParams();
  const q = params.get('q') || '';
  const [products, setProducts] = useState([]);

  useEffect(() => {
    if (q) {
      fetch(`${API_URL}/api/products?search=${encodeURIComponent(q)}&limit=50`)
        .then(r => r.json())
        .then(d => setProducts(d.data))
        .catch(() => {});
    }
  }, [q]);

  return (
    <div className="bk-page" data-testid="search-page">
      <h2 className="bk-page-title">Search results for "{q}"</h2>
      <div className="bk-products-grid">
        {products.map(p => <ProductCard key={p.product_id} product={p} />)}
        {products.length === 0 && <p className="bk-no-data">No products found for "{q}"</p>}
      </div>
    </div>
  );
}

// ---- Product Detail ----
function ProductDetailPage() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const { addToCart, cart, updateCart, token } = useApp();
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API_URL}/api/products/${id}`)
      .then(r => r.json())
      .then(d => setProduct(d))
      .catch(() => {});
  }, [id]);

  if (!product) return <div className="bk-page"><p>Loading...</p></div>;

  const price = discountedPrice(product.price, product.discount);
  const cartItem = cart.find(c => c.product_id === product.product_id);

  return (
    <div className="bk-page bk-product-detail" data-testid="product-detail-page">
      <div className="bk-pd-left">
        <img src={product.image} alt={product.name} onError={e => { e.target.src = 'https://via.placeholder.com/400?text=Product'; }} />
      </div>
      <div className="bk-pd-right">
        <div className="bk-delivery-time">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0C831F" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          <span>10 MINS</span>
        </div>
        <h1>{product.name}</h1>
        <p className="bk-pd-unit">{product.unit}</p>
        <div className="bk-pd-prices">
          <span className="bk-price-now bk-price-lg">{formatPrice(price)}</span>
          {product.discount > 0 && (
            <>
              <span className="bk-price-old">{formatPrice(product.price)}</span>
              <span className="bk-discount-tag">{product.discount}% OFF</span>
            </>
          )}
        </div>
        <p className="bk-pd-desc">{product.description}</p>
        <div className="bk-pd-actions">
          {cartItem ? (
            <div className="bk-qty-control bk-qty-lg">
              <button onClick={() => updateCart(cartItem.cart_item_id, cartItem.quantity - 1)}>-</button>
              <span>{cartItem.quantity}</span>
              <button onClick={() => updateCart(cartItem.cart_item_id, cartItem.quantity + 1)}>+</button>
            </div>
          ) : (
            <button className="bk-btn-primary bk-btn-lg" onClick={() => { if (!token) navigate('/login'); else addToCart(product.product_id); }} data-testid="add-to-cart-detail">Add to Cart</button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---- Login Page ----
function LoginPage() {
  const { login } = useApp();
  const navigate = useNavigate();
  const [tab, setTab] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '', mobile: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const url = tab === 'login' ? `${API_URL}/api/auth/login` : `${API_URL}/api/auth/register`;
      const body = tab === 'login' ? { email: form.email, password: form.password } : form;
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) { setError(d.detail || 'Error'); return; }
      login(d.token, d);
      navigate('/');
    } catch(e) { setError('Connection failed'); }
    finally { setLoading(false); }
  };

  const quickLogin = async () => {
    setLoading(true); setError('');
    try {
      const r = await fetch(`${API_URL}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'demo@blinkit2.com', password: 'password123' }) });
      const d = await r.json();
      if (r.ok) { login(d.token, d); navigate('/'); }
      else setError(d.detail);
    } catch(e) { setError('Failed'); }
    finally { setLoading(false); }
  };

  return (
    <div className="bk-auth-page" data-testid="login-page">
      <div className="bk-auth-card">
        <div className="bk-auth-logo">
          <div className="bk-logo-icon">B</div>
          <h1>blinkit2</h1>
        </div>
        <div className="bk-auth-tabs">
          <button className={tab === 'login' ? 'active' : ''} onClick={() => setTab('login')} data-testid="login-tab">Login</button>
          <button className={tab === 'register' ? 'active' : ''} onClick={() => setTab('register')} data-testid="register-tab">Register</button>
        </div>
        <form onSubmit={handleSubmit} className="bk-auth-form">
          {tab === 'register' && (
            <>
              <input placeholder="Full Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} required data-testid="register-name-input" />
              <input placeholder="Mobile Number" value={form.mobile} onChange={e => setForm({...form, mobile: e.target.value})} data-testid="register-mobile-input" />
            </>
          )}
          <input type="email" placeholder="Email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} required data-testid="email-input" />
          <input type="password" placeholder="Password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} required data-testid="password-input" />
          {error && <p className="bk-error">{error}</p>}
          <button type="submit" className="bk-btn-primary" disabled={loading} data-testid="auth-submit-btn">
            {loading ? 'Please wait...' : tab === 'login' ? 'Login' : 'Register'}
          </button>
        </form>
        <div className="bk-quick-login">
          <button onClick={quickLogin} className="bk-quick-btn" data-testid="quick-login-btn">
            Quick Login as Demo User
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Checkout Page ----
function CheckoutPage() {
  const { cart, totalPrice, authHeader, fetchCart } = useApp();
  const navigate = useNavigate();
  const [address, setAddress] = useState({ address_line: '', city: '', state: '', pincode: '', mobile: '' });
  const [placing, setPlacing] = useState(false);
  const [orderId, setOrderId] = useState(null);
  const deliveryFee = totalPrice >= 199 ? 0 : 25;

  const handleOrder = async (e) => {
    e.preventDefault();
    setPlacing(true);
    try {
      // Save address first
      const ar = await fetch(`${API_URL}/api/addresses?authorization=${encodeURIComponent(authHeader)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(address)
      });
      const ad = await ar.json();

      // Place order
      const or_ = await fetch(`${API_URL}/api/orders?authorization=${encodeURIComponent(authHeader)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address_id: ad.address_id, payment_method: 'cod' })
      });
      const od = await or_.json();
      if (or_.ok) {
        setOrderId(od.order_id);
        fetchCart();
      }
    } catch(e) {}
    finally { setPlacing(false); }
  };

  if (orderId) {
    return (
      <div className="bk-page bk-order-success" data-testid="order-success">
        <div className="bk-success-card">
          <div className="bk-success-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#0C831F" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
          </div>
          <h2>Order Placed!</h2>
          <p className="bk-order-id">Order ID: {orderId}</p>
          <div className="bk-delivery-eta">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0C831F" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            <span>Arriving in <strong>10 minutes</strong></span>
          </div>
          <button className="bk-btn-primary" onClick={() => navigate('/')} data-testid="continue-shopping-btn">Continue Shopping</button>
          <Link to="/orders" className="bk-link" data-testid="view-orders-link">View My Orders</Link>
        </div>
      </div>
    );
  }

  if (cart.length === 0) {
    return (
      <div className="bk-page bk-cart-empty-page" data-testid="empty-cart-checkout">
        <h2>Your cart is empty</h2>
        <button className="bk-btn-primary" onClick={() => navigate('/')}>Shop Now</button>
      </div>
    );
  }

  return (
    <div className="bk-page bk-checkout" data-testid="checkout-page">
      <div className="bk-checkout-left">
        <h2>Delivery Address</h2>
        <form onSubmit={handleOrder} className="bk-address-form">
          <input placeholder="Address Line" value={address.address_line} onChange={e => setAddress({...address, address_line: e.target.value})} required data-testid="address-input" />
          <div className="bk-form-row">
            <input placeholder="City" value={address.city} onChange={e => setAddress({...address, city: e.target.value})} required data-testid="city-input" />
            <input placeholder="State" value={address.state} onChange={e => setAddress({...address, state: e.target.value})} required data-testid="state-input" />
          </div>
          <div className="bk-form-row">
            <input placeholder="Pincode" value={address.pincode} onChange={e => setAddress({...address, pincode: e.target.value})} required data-testid="pincode-input" />
            <input placeholder="Mobile Number" value={address.mobile} onChange={e => setAddress({...address, mobile: e.target.value})} required data-testid="mobile-input" />
          </div>
          <div className="bk-payment-method">
            <h3>Payment Method</h3>
            <label className="bk-radio"><input type="radio" name="payment" value="cod" defaultChecked /> Cash on Delivery</label>
          </div>
          <button type="submit" className="bk-btn-primary bk-btn-lg" disabled={placing} data-testid="place-order-btn">
            {placing ? 'Placing Order...' : `Place Order - ${formatPrice(totalPrice + deliveryFee)}`}
          </button>
        </form>
      </div>
      <div className="bk-checkout-right">
        <div className="bk-order-summary">
          <h3>Order Summary</h3>
          {cart.map(item => (
            <div key={item.cart_item_id} className="bk-summary-item">
              <span>{item.product.name} x {item.quantity}</span>
              <span>{formatPrice(discountedPrice(item.product.price, item.product.discount) * item.quantity)}</span>
            </div>
          ))}
          <div className="bk-summary-divider" />
          <div className="bk-summary-item"><span>Items total</span><span>{formatPrice(totalPrice)}</span></div>
          <div className="bk-summary-item"><span>Delivery</span><span>{deliveryFee === 0 ? 'FREE' : formatPrice(deliveryFee)}</span></div>
          <div className="bk-summary-item bk-summary-total"><span>Total</span><span>{formatPrice(totalPrice + deliveryFee)}</span></div>
        </div>
      </div>
    </div>
  );
}

// ---- Orders Page ----
function OrdersPage() {
  const { authHeader } = useApp();
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    fetch(`${API_URL}/api/orders?authorization=${encodeURIComponent(authHeader)}`)
      .then(r => r.json())
      .then(d => setOrders(d.data))
      .catch(() => {});
  }, [authHeader]);

  return (
    <div className="bk-page" data-testid="orders-page">
      <h2 className="bk-page-title">My Orders</h2>
      {orders.length === 0 ? (
        <p className="bk-no-data">No orders yet</p>
      ) : (
        <div className="bk-orders-list">
          {orders.map(order => (
            <div key={order.order_id} className="bk-order-card" data-testid={`order-${order.order_id}`}>
              <div className="bk-order-card-header">
                <div>
                  <span className="bk-order-id-label">Order #{order.order_id}</span>
                  <span className="bk-order-date">{new Date(order.created_at).toLocaleDateString()}</span>
                </div>
                <span className={`bk-order-status bk-status-${order.status}`}>{order.status}</span>
              </div>
              <div className="bk-order-items-preview">
                {order.items.map((item, i) => (
                  <div key={i} className="bk-order-item-mini">
                    <img src={item.image} alt={item.name} onError={e => { e.target.src = 'https://via.placeholder.com/40'; }} />
                    <span>{item.name} x{item.quantity}</span>
                  </div>
                ))}
              </div>
              <div className="bk-order-card-footer">
                <span>Total: <strong>{formatPrice(order.total)}</strong></span>
                <span className="bk-order-delivery">Delivered in {order.estimated_delivery}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- Footer ----
function Footer() {
  return (
    <footer className="bk-footer" data-testid="footer">
      <div className="bk-footer-inner">
        <p>&copy; 2026 blinkit2 &mdash; Groceries delivered in 10 minutes</p>
      </div>
    </footer>
  );
}

// ---- App ----
function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Header />
        <main className="bk-main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/category/:id" element={<CategoryPage />} />
            <Route path="/product/:id" element={<ProductDetailPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/checkout" element={<CheckoutPage />} />
            <Route path="/orders" element={<OrdersPage />} />
          </Routes>
        </main>
        <CartSidebar />
        <Footer />
      </AppProvider>
    </BrowserRouter>
  );
}

export default App;
