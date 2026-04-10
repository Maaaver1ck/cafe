import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define new JS block
new_script = """<script>
        const API_BASE = 'http://localhost:3000/api';

        // 模拟商品数据
        const mockProducts = [
            { id: 1, name: "高端机械键盘", price: 599.00, image: "https://via.placeholder.com/250x200?text=Keyboard" },
            { id: 2, name: "无线降噪耳机", price: 1299.00, image: "https://via.placeholder.com/250x200?text=Headphones" },
            { id: 3, name: "电竞游戏鼠标", price: 299.00, image: "https://via.placeholder.com/250x200?text=Mouse" },
            { id: 4, name: "27寸4K显示器", price: 1999.00, image: "https://via.placeholder.com/250x200?text=Monitor" },
            { id: 5, name: "智能手表", price: 899.00, image: "https://via.placeholder.com/250x200?text=Smartwatch" },
            { id: 6, name: "便携移动电源", price: 129.00, image: "https://via.placeholder.com/250x200?text=Powerbank" }
        ];

        // 状态管理
        let cart = [];
        let currentUser = null; // { phone: '...', id: ... }
        let currentPaymentMethod = 'wechat';
        let currentOrderId = null; // 当前正在支付的订单号

        // 初始化页面
        function init() {
            renderProducts();
            updateCartUI();
        }

        // 切换视图
        function switchView(viewId) {
            if (viewId === 'profile' && !currentUser) {
                showToast('请先绑定手机号登录');
                showModal('login-modal');
                return;
            }

            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-links button').forEach(el => el.classList.remove('active'));

            document.getElementById(`view-${viewId}`).classList.add('active');
            document.getElementById(`nav-${viewId}`).classList.add('active');

            if (viewId === 'profile') {
                renderProfile();
            }
        }

        function renderProducts() {
            const container = document.getElementById('product-container');
            container.innerHTML = mockProducts.map(product => `
                <div class="product-card">
                    <img src="${product.image}" alt="${product.name}" class="product-image">
                    <h3 class="product-title">${product.name}</h3>
                    <p class="product-price">¥${product.price.toFixed(2)}</p>
                    <button class="btn" onclick="addToCart(${product.id})">加入购物车</button>
                </div>
            `).join('');
        }

        function addToCart(productId) {
            const product = mockProducts.find(p => p.id === productId);
            const existingItem = cart.find(item => item.id === productId);
            if (existingItem) existingItem.quantity += 1;
            else cart.push({ ...product, quantity: 1 });
            showToast(`已将 ${product.name} 加入购物车`);
            updateCartUI();
        }

        function removeFromCart(productId) {
            cart = cart.filter(item => item.id !== productId);
            updateCartUI();
        }

        function updateQuantity(productId, delta) {
            const item = cart.find(item => item.id === productId);
            if (item) {
                item.quantity += delta;
                if (item.quantity <= 0) removeFromCart(productId);
                else updateCartUI();
            }
        }

        function updateCartUI() {
            const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
            const badge = document.getElementById('cart-badge');
            if (totalItems > 0) {
                badge.style.display = 'inline-block';
                badge.textContent = totalItems;
            } else {
                badge.style.display = 'none';
            }

            const container = document.getElementById('cart-items-container');
            const cartContent = document.getElementById('cart-content');
            const emptyMsg = document.getElementById('cart-empty-message');

            if (cart.length === 0) {
                cartContent.style.display = 'none';
                emptyMsg.style.display = 'block';
            } else {
                cartContent.style.display = 'block';
                emptyMsg.style.display = 'none';

                container.innerHTML = cart.map(item => `
                    <div class="cart-item">
                        <div class="cart-item-info">
                            <img src="${item.image}" alt="${item.name}" class="cart-item-img">
                            <div>
                                <div style="font-weight:bold;">${item.name}</div>
                                <div style="color: #e53935;">¥${item.price.toFixed(2)}</div>
                            </div>
                        </div>
                        <div class="cart-controls">
                            <button onclick="updateQuantity(${item.id}, -1)">-</button>
                            <span style="margin: 0 10px;">${item.quantity}</span>
                            <button onclick="updateQuantity(${item.id}, 1)">+</button>
                            <button style="margin-left: 1rem; color: #dc3545; border: none; background: none; text-decoration: underline;" onclick="removeFromCart(${item.id})">删除</button>
                        </div>
                    </div>
                `).join('');
            }

            const totalPrice = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
            document.getElementById('cart-total-price').textContent = totalPrice.toFixed(2);
        }

        async function checkout() {
            if (cart.length === 0) return;
            if (!currentUser) {
                showToast('请先绑定手机号登录后再结算');
                showModal('login-modal');
                return;
            }

            // 唤起后端生成订单
            try {
                const res = await fetch(API_BASE + '/orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId: currentUser.id, items: cart })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || '生成订单失败');
                
                currentOrderId = data.orderId;
                document.getElementById('pay-amount').textContent = data.totalAmount.toFixed(2);
                
                // 设置支付二维码占位符
                selectPayment(currentPaymentMethod);
                
                showModal('payment-modal');
            } catch (err) {
                showToast(err.message);
            }
        }

        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.style.display = 'block';
            setTimeout(() => toast.style.display = 'none', 2000);
        }

        function showModal(modalId) { document.getElementById(modalId).style.display = 'flex'; }
        function closeModal(modalId) { document.getElementById(modalId).style.display = 'none'; }

        async function sendCode() {
            const phone = document.getElementById('phone-input').value;
            if (!/^1[3-9]\d{9}$/.test(phone)) {
                showToast('请输入正确的11位手机号');
                return;
            }

            const btn = document.getElementById('btn-get-code');
            btn.disabled = true;
            
            try {
                const res = await fetch(API_BASE + '/send-code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone })
                });
                if (!res.ok) throw new Error('发送失败');
                
                showToast('验证码已发送，请查看后端控制台');
                
                let countdown = 60;
                const timer = setInterval(() => {
                    countdown--;
                    btn.textContent = `${countdown}s 后重试`;
                    if (countdown <= 0) {
                        clearInterval(timer);
                        btn.textContent = '获取验证码';
                        btn.disabled = false;
                    }
                }, 1000);
            } catch (err) {
                showToast(err.message);
                btn.disabled = false;
            }
        }

        async function verifyLogin() {
            const phone = document.getElementById('phone-input').value;
            const code = document.getElementById('code-input').value;

            if (!/^1[3-9]\d{9}$/.test(phone)) {
                showToast('请输入正确的11位手机号');
                return;
            }

            try {
                const res = await fetch(API_BASE + '/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone, code })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || '登录失败');

                currentUser = { phone: data.phone, id: data.id };
                showToast('登录成功！');
                closeModal('login-modal');
                
                if (document.getElementById('view-cart').classList.contains('active') && cart.length > 0) {
                    checkout();
                } else if (!document.getElementById('view-cart').classList.contains('active') && !document.getElementById('view-products').classList.contains('active')) {
                    switchView('profile');
                }
            } catch (err) {
                showToast(err.message);
            }
        }

        function selectPayment(method) {
            currentPaymentMethod = method;
            document.querySelectorAll('.payment-method').forEach(el => el.classList.remove('selected'));
            document.getElementById(`pay-${method}`).classList.add('selected');
            
            const qrArea = document.getElementById('qr-code-area');
            if (method === 'wechat') {
                qrArea.innerHTML = `请使用微信扫码支付<br>(模拟真实订单: ${currentOrderId||''})`;
            } else {
                qrArea.innerHTML = `请使用支付宝扫码支付<br>(模拟真实订单: ${currentOrderId||''})`;
            }
        }

        async function processPayment() {
            if (!currentOrderId) return;
            
            try {
                const res = await fetch(API_BASE + '/pay/callback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ orderId: currentOrderId, status: 'SUCCESS' })
                });
                
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.error || '支付回调失败');
                }
                
                showToast(`支付成功！第三方网关已回调`);
                closeModal('payment-modal');
                currentOrderId = null;
                
                cart = [];
                updateCartUI();
                
                switchView('profile');
            } catch (err) {
                showToast(err.message);
            }
        }

        async function renderProfile() {
            const profileSection = document.getElementById('view-profile');
            if (!currentUser) {
                profileSection.innerHTML = '';
                return;
            }

            const maskedPhone = currentUser.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
            
            profileSection.innerHTML = `
                <div class="profile-container">
                    <div class="user-info">
                        <div class="avatar">${currentUser.phone.substring(0, 1)}</div>
                        <div style="flex: 1;">
                            <h2>用户 ${maskedPhone}</h2>
                            <p style="color: #666;">ID: ${currentUser.id}</p>
                            <p style="color: #666;">等级: 注册会员</p>
                        </div>
                        <button class="btn" style="width: auto; background-color: #f44336; padding: 0.5rem 1rem;" onclick="logout()">退出登录</button>
                    </div>
                    <div class="order-history">
                        <h3 style="border-bottom: 2px solid var(--primary-color); padding-bottom: 0.5rem; display: inline-block;">历史订单</h3>
                        <div id="orders-list-container" style="margin-top: 1rem;">加载中...</div>
                    </div>
                </div>
            `;

            try {
                const res = await fetch(API_BASE + '/orders/' + currentUser.id);
                const orders = await res.json();
                
                const container = document.getElementById('orders-list-container');
                if (orders.length === 0) {
                    container.innerHTML = '<p style="color: #666; text-align: center; padding: 2rem;">暂无历史订单，快去购物吧！</p>';
                } else {
                    container.innerHTML = orders.map(order => `
                        <div class="order-item">
                            <div>
                                <strong>订单号: ${order.id}</strong>
                                <p style="color: #666; font-size: 0.9rem;">时间: ${order.date}</p>
                                <p style="color: #666; font-size: 0.9rem;">包含: ${order.items[0].name} ${order.items.length > 1 ? `等 ${order.items.reduce((s,i)=>s+i.quantity,0)} 件商品` : ''}</p>
                            </div>
                            <div style="text-align: right;">
                                <span style="color: green; font-weight: bold;">${order.status}</span>
                                <p style="font-weight: bold; margin-top: 0.5rem; font-size: 1.1rem;">¥${order.total.toFixed(2)}</p>
                            </div>
                        </div>
                    `).join('');
                }
            } catch(err) {
                document.getElementById('orders-list-container').innerHTML = '<p style="color: red;">拉取订单失败</p>';
            }
        }

        function logout() {
            currentUser = null;
            showToast('已退出登录');
            switchView('products');
        }

        init();
    </script>"""

new_content = re.sub(r'<script>.*?</script>', new_script, content, flags=re.DOTALL)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Updated index.html")
