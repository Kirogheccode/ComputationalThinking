let loadingDiv = null;
let uploadedImage = null;
let isProcess = false;

function scrollAnimation() {
    // Initialize AOS for scroll animations
    if (window.AOS) {
        AOS.init({
            duration: 700,
            easing: 'ease-out-cubic',
            once: false,
            offset: 80
        });
    }
    // Smooth scroll for hero CTA
    document.querySelectorAll('.hero-cta').forEach(a => {
        a.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

}

function foodModal() {
    // --- Logic for Food Modal on Homepage (improved) ---
    var foodModal = document.getElementById('foodModal');
    if (foodModal) {
        foodModal.addEventListener('show.bs.modal', function (event) {
            var card = event.relatedTarget;
            if (!card) return;

            var name = card.getAttribute('data-name') || 'Không tên';
            var description = card.getAttribute('data-description') || 'Không có mô tả';
            var location = card.getAttribute('data-location') || '-';
            var price = card.getAttribute('data-price') || '-';
            var image = card.getAttribute('data-image') || '/static/images/placeholder-food.jpg';

            var modalTitle = foodModal.querySelector('.modal-title');
            var modalImage = foodModal.querySelector('#modalFoodImage');
            var modalDescription = foodModal.querySelector('#modalFoodDescription');
            var modalLocation = foodModal.querySelector('#modalFoodLocation');
            var modalPrice = foodModal.querySelector('#modalFoodPrice');
            var openMapBtn = foodModal.querySelector('#openMapBtn');

            modalTitle.textContent = name;
            modalImage.src = image;
            modalDescription.textContent = description;
            modalLocation.textContent = location;
            modalPrice.textContent = price;

            // openMapBtn can link to map page with query params (simple)
            openMapBtn.href = `/map?name=${encodeURIComponent(name)}&location=${encodeURIComponent(location)}`;
        });
    }
}

function filterAndSearch() {
    // --- Filter & Search (client-side simple) ---
    const areaSelect = document.getElementById('areaSelect');
    const searchInput = document.getElementById('searchInput');
    const clearFilters = document.getElementById('clearFilters');
    const foodsGrid = document.getElementById('foodsGrid');
    const foodItems = Array.from(document.querySelectorAll('.food-item'));

    function applyFilters() {
        const area = (areaSelect?.value || 'all').toLowerCase();
        const q = (searchInput?.value || '').trim().toLowerCase();

        foodItems.forEach(item => {
            const itemArea = (item.getAttribute('data-area') || '').toLowerCase();
            const name = (item.getAttribute('data-name') || '').toLowerCase();
            const matchArea = (area === 'all') || itemArea.includes(area);
            const matchQuery = q === '' || name.includes(q);
            item.style.display = (matchArea && matchQuery) ? '' : 'none';
        });

        // refresh AOS (if used)
        if (window.AOS) AOS.refresh();
    }

    if (areaSelect) areaSelect.addEventListener('change', applyFilters);
    if (searchInput) searchInput.addEventListener('input', () => {
        // debounce quick
        clearTimeout(window.__searchDeb);
        window.__searchDeb = setTimeout(applyFilters, 200);
    });
    if (clearFilters) clearFilters.addEventListener('click', () => {
        if (areaSelect) areaSelect.value = 'all';
        if (searchInput) searchInput.value = '';
        applyFilters();
    });
}
function mapModal() {
    let map; // Biến toàn cục giữ bản đồ
    let routeLayer; // Biến giữ đường vẽ
    let destinationMarker;
    const mapModal = document.getElementById('mapModal');
    if (mapModal) { // Kiểm tra xem element có tồn tại không
        // 1. Khởi tạo bản đồ khi Modal mở ra
        mapModal.addEventListener('shown.bs.modal', async function (event) {
            // Nếu bản đồ chưa được khởi tạo thì tạo mới
            if (!map) {
                // Lưu ý: ID của div bản đồ trong HTML mới là 'map', không phải 'mapContainer'
                map = L.map('map').setView([10.762622, 106.660172], 13);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors'
                }).addTo(map);
            } else {
                setTimeout(() => { map.invalidateSize(); }, 200); // Fix lỗi hiển thị map
            }

            // Lấy thông tin từ nút bấm
            const button = event.relatedTarget;
            let destinationAddress = "";
            if (button) {
                destinationAddress = button.getAttribute('data-location');
                const destinationInput = document.getElementById('destinationHidden');
                if (destinationInput) destinationInput.value = destinationAddress;
            }

            if (routeLayer) map.removeLayer(routeLayer);
            if (destinationMarker) map.removeLayer(destinationMarker);

            if (destinationAddress) {
                try {
                    // Gọi API backend để lấy tọa độ từ địa chỉ
                    const response = await fetch('/api/geocode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ address: destinationAddress })
                    });

                    const data = await response.json();

                    if (data.lat && data.lng) {
                        // Tạo marker màu đỏ (hoặc mặc định) tại vị trí quán
                        destinationMarker = L.marker([data.lat, data.lng]).addTo(map);

                        // Thêm popup hiển thị địa chỉ
                        destinationMarker.bindPopup(`<b>Vị trí quán ăn</b><br>${destinationAddress}`).openPopup();

                        // Zoom bản đồ vào ngay vị trí quán
                        map.setView([data.lat, data.lng], 16);
                    } else {
                        console.warn("Không tìm thấy tọa độ quán để mark.");
                    }
                } catch (err) {
                    console.error("Lỗi khi lấy tọa độ quán:", err);
                }
            }
            // Reset ô nhập
            const originInput = document.getElementById('userOriginInput');
            if (originInput) {
                originInput.value = '';
                originInput.focus();
            }

            // Xóa đường cũ
            // if (routeLayer) map.removeLayer(routeLayer);
        });

        // 2. Xử lý sự kiện nút "Tìm đường"
        const btnFindRoute = document.getElementById('btnFindRoute');
        if (btnFindRoute) {
            btnFindRoute.addEventListener('click', async function () {
                const originInput = document.getElementById('userOriginInput');
                const destInput = document.getElementById('destinationHidden');

                const origin = originInput ? originInput.value : '';
                const destination = destInput ? destInput.value : '';

                if (!origin) {
                    alert("Vui lòng nhập vị trí của bạn!");
                    return;
                }

                this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tìm...';

                try {
                    const response = await fetch('/api/find_path', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ origin: origin, destination: destination })
                    });

                    const data = await response.json();

                    if (data.error) {
                        alert("Lỗi: " + data.error);
                    } else {
                        if (routeLayer) map.removeLayer(routeLayer);

                        // Đảo ngược tọa độ cho Leaflet [lat, lon]
                        const latLngs = data.geometry.map(coord => [coord[1], coord[0]]);

                        routeLayer = L.polyline(latLngs, { color: 'blue', weight: 5 }).addTo(map);
                        map.fitBounds(routeLayer.getBounds());

                        // Thêm Marker
                        L.marker(data.start_point).addTo(map).bindPopup("Bạn ở đây").openPopup();
                        L.marker(data.end_point).addTo(map).bindPopup("Quán ăn");
                    }

                } catch (err) {
                    console.error(err);
                    alert("Có lỗi xảy ra khi tìm đường.");
                } finally {
                    this.innerHTML = '<i class="fa-solid fa-route"></i> Tìm đường';
                }
            });
        }
    }
}

function displayUserMessage(messageText, chatWindow){
    const userMessageDiv = document.createElement('div');
    userMessageDiv.classList.add('message', 'user-message');
    userMessageDiv.innerHTML = `<p>${messageText}</p>`;
    chatWindow.appendChild(userMessageDiv);
    userInput.value = '';
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function createLoadingBubble(chatWindow){
    loadingDiv = document.createElement('div');
    loadingDiv.classList.add('message', 'bot-message', 'loading-message');
    loadingDiv.innerHTML = `<p></p>`;
    chatWindow.appendChild(loadingDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeLoadingBubble(){
    if (loadingDiv) {
        loadingDiv.remove();
        loadingDiv = null; // tránh lỗi nếu gọi remove nhiều lần
    }
}

function displayBotMessage(botText, chatWindow) 
{
    if(botText=="")
        return;
    const botMessageDiv = document.createElement('div');
    botMessageDiv.classList.add('message', 'bot-message', 'd-flex', 'align-items-start');
    botMessageDiv.innerHTML = `
        <img src="/static/images/jane.jpg" class="bot-avatar" alt="Bot Avatar">
        <p>${botText}</p>
    `;
    chatWindow.appendChild(botMessageDiv);

    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendText(messageText, displayUser = true){
    isProcess = true;
    const imageBtn = document.getElementById('imageInputBtn');
    const imageInput = document.getElementById('imageInput');
    const previewWrapper = document.getElementById('imagePreviewWrapper')
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('userInput');


    // Display user message
    if(displayUser == true){
        displayUserMessage(messageText, chatWindow);
    }

    if (userInput) {
        userInput.value = '';
    }

    // Create loading bubble
    createLoadingBubble(chatWindow);

    // Call Gemini API
    // 3. GỌI API BACKEND (thay vì gọi gemini.js)
    let botText = ""; // Biến để lưu tin nhắn trả lời
    try {
        // Gửi yêu cầu POST đến endpoint /api/chat của Flask
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            // Gửi tin nhắn dưới dạng JSON
            body: JSON.stringify({ message: messageText })
        });

        if (!response.ok) {
            // Xử lý lỗi nếu server trả về 4xx, 5xx
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Nhận dữ liệu JSON trả về
        const data = await response.json();
        console.log("DEBUG: toàn bộ data nhận về từ API:", data);
            
        // Lấy nội dung trả lời từ key 'reply' (đã định nghĩa trong app.py)
        botText = data.reply;

        // RẤT QUAN TRỌNG: Thay thế ký tự xuống dòng (\n) bằng thẻ <br>
        // để chúng hiển thị đúng trong HTML
        botText = botText.replace(/\n/g, '<br>');
        const container = document.getElementById("carousel");
        renderFoodCards(container, data.food_data);

    }
    catch (err) {
        console.error("Lỗi khi gọi API:", err);
        botText = "Xin lỗi, hệ thống đang gặp sự cố. Bạn vui lòng thử lại sau.";
    }

    // Remove loading bubble
    removeLoadingBubble();

    // Display bot response
    displayBotMessage(botText, chatWindow);
    isProcess = false;
}

async function sendImage(text) {
    isProcess = true;
    const chatWindow = document.getElementById('chat-window');
    const imageInput = document.getElementById('imageInput');
    const previewWrapper = document.getElementById('imagePreviewWrapper');
    const previewImg = document.getElementById('imagePreview');

    if (!uploadedImage) return;

    // 1. Hiển thị ảnh trong chat
    const imgURL = URL.createObjectURL(uploadedImage);

    const imageBubble = document.createElement('div');
    imageBubble.classList.add('message', 'user-message');

    imageBubble.innerHTML = `
        <div class="user-image-wrapper">
            <img src="${imgURL}" class="user-chat-image" alt="uploaded image">
        </div>
    `;

    chatWindow.appendChild(imageBubble);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    // 2. Tạo loading bubble cho bot
    createLoadingBubble(chatWindow);

    // 3. Gửi ảnh lên backend (nếu có API)
    let botText = "";
    let food_predict = "";
    try {
        const formData = new FormData();
        formData.append("image", uploadedImage);

        const response = await fetch('/api/predict', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        botText = data.message;
        food_predict = data.food_name;
    } catch (err) {
        console.error("Lỗi khi gửi ảnh:", err);
        botText = "Xin lỗi, hệ thống gặp sự cố khi gửi ảnh.";
    }

    // 4. Xoá loading bubble
    removeLoadingBubble();

    // 5. Hiển thị tin nhắn trả lời từ bot
    displayBotMessage(botText, chatWindow);

    // 6. Reset preview và input
    uploadedImage = null;
    previewImg.src = '';
    previewWrapper.classList.add('d-none');
    imageInput.value = '';

    const combinedText = (food_predict || '') + " " + (text || '') ;
    sendText(combinedText, false);
}

function showNotification(text) {
    const container = document.getElementById('notificationContainer');
    if (!container) {
        console.error("Notification container not found!");
        return;
    }

    // 1. Tạo phần tử thông báo
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = text;
    
    // Thêm icon nếu cần (tùy chọn)
    notification.innerHTML = `<i class="fa-solid fa-check-circle me-2"></i>${text}`;

    // 2. Thêm vào container và hiển thị
    container.appendChild(notification);
    
    // Sử dụng setTimeout để thêm class 'show' sau một chút để kích hoạt transition
    setTimeout(() => {
        notification.classList.add('show');
    }, 10); // Độ trễ nhỏ

    // 3. Thiết lập tự động biến mất sau 2 giây (2000ms)
    setTimeout(() => {
        // Bắt đầu hiệu ứng ẩn
        notification.classList.remove('show');
        
        // Sau khi hiệu ứng ẩn hoàn tất (0.3s theo CSS), loại bỏ phần tử khỏi DOM
        setTimeout(() => {
            if (container.contains(notification)) {
                container.removeChild(notification);
            }
        }, 300); // 300ms phải khớp với transition trong CSS
        
    }, 2000); // Thời gian hiển thị (2 giây)
}

async function sendMessage(uploadedImage, text) {
    if(isProcess){
        showNotification("Đang xử lý tác vụ, hãy đợi cho đến khi thực hiện xong!");
        return;
    }

    if(text == ""){
        showNotification("Hãy nhập liệu vào ô input.");
        return;
    }

    // Nếu có ảnh -> gửi ảnh
    if (uploadedImage && text!=="") {
        await sendImage(text);
        return;
    }

    // Nếu không có ảnh -> gửi text
    if (text !== "") {
        await sendText(text);
        return;
    }
}

function chatBot() {
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const userInput = document.getElementById('userInput');
    const chatWindow = document.getElementById('chat-window');

    sendMessageBtn.addEventListener('click', () => {
        const text = userInput.value.trim();
        sendMessage(uploadedImage, text);
    });
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const text = userInput.value.trim();
            sendMessage(uploadedImage, text);
        }
    });
}

function themeMode() {
    // --- Theme toggle (dark mode) ---
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const body = document.body;
    // === Theme initialization ===
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "dark") {
        body.classList.add("dark");
        if (themeToggleBtn)
            themeToggleBtn.textContent = "🌙 Tối";
    }
    else {
        body.classList.remove("dark");
        if (themeToggleBtn)
            themeToggleBtn.textContent = "🌞 Sáng";
    }


    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            const isDark = body.classList.toggle("dark");
            themeToggleBtn.textContent = isDark ? "🌙 Tối" : "🌞 Sáng";
            localStorage.setItem("theme", isDark ? "dark" : "light");
            if (window.AOS) setTimeout(() => AOS.refresh(), 350);
        });
    }
}

function renderFoodCards(container, data) {
    const placeholder = document.getElementById("food-placeholder");

    // 1. XÓA các card cũ trước khi render mới
    const cards = container.querySelectorAll('.card-food');
    cards.forEach(card => card.remove()); // xóa card cũ, giữ placeholder

    // 2. Nếu có data → ẩn placeholder
    if (data && data.length > 0) {
        if (placeholder) {
            placeholder.style.display = "none";
        }
    } 
    // 3. Nếu KHÔNG có dữ liệu → hiện placeholder và thoát hàm
    else {
        if (placeholder) {
            placeholder.style.display = "flex"; // dùng flex để căn giữa
        }
        return;
    }

    // 4. Render các card mới
    data.forEach(food => {
    const card = document.createElement('div');
    card.classList.add('card-food');

    // Fallback ảnh mặc định
    const imageSrc = food.img && food.img.trim() !== ""
        ? `/static/${food.img}`
        : "/static/images/default_food.jpg";

    card.innerHTML = `
        <img src="${imageSrc}" alt="${food.Name}">
        <div class="food-info">
            <h5 class="food-name">${food.Name}</h5>
            <p class="food-location">Địa chỉ: ${food.Address}</p>
            <p class="food-rating">Đánh giá: ${food.Rating} ⭐</p>
            <p class="food-description">Mô tả: ${food.Description}</p>
            <p class="food-distance">Khoảng cách: ${food.distance_km} km</p>
        </div>
        <button class="location-btn location-dot"
                title="Xem trên bản đồ"
                data-bs-toggle="modal"
                data-bs-target="#mapModal"
                data-name="${food.Name}"
                data-rating="${food.Rating}"
                data-location="${food.Address}"
                data-image="${imageSrc}">
            <i class="fa-solid fa-location-dot"></i>
        </button>
    `;
    container.appendChild(card);
});

}

function displayImage(chatWindow, uploadedImage) {
    if (!uploadedImage) return;

    const imgURL = URL.createObjectURL(uploadedImage);

    const imageBubble = document.createElement('div');
    imageBubble.classList.add('message', 'user-message');

    imageBubble.innerHTML = `
        <img src="${imgURL}" class="chat-image" alt="uploaded image">
    `;

    chatWindow.appendChild(imageBubble);

    // Tự động cuộn xuống
    chatWindow.scrollTop = chatWindow.scrollHeight;
}


function uploadImageFeature() {
    const imageBtn = document.getElementById('imageInputBtn');
    const imageInput = document.getElementById('imageInput');
    const previewWrapper = document.getElementById('imagePreviewWrapper');
    const previewImg = document.getElementById('imagePreview');
    const removeBtn = document.getElementById('removeImageBtn');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const userInput = document.getElementById('userInput');
    const chatWindow = document.getElementById('chat-window');

    // --- Mở file picker ---
    imageBtn.addEventListener('click', () => {
        imageInput.click();
    });

    // --- Khi chọn ảnh ---
    imageInput.addEventListener('change', () => {
        const file = imageInput.files[0];
        if (!file) return;

        // Giới hạn 1 ảnh
        uploadedImage = file;

        // Hiển thị preview
        const url = URL.createObjectURL(file);
        previewImg.src = url;

        previewWrapper.classList.remove('d-none');
    });

    // --- Xoá ảnh ---
    removeBtn.addEventListener('click', () => {
        uploadedImage = null;
        previewImg.src = '';
        previewWrapper.classList.add('d-none');
        imageInput.value = ''; // reset input file
    });
    const text = userInput.value.trim();

}

function main()
{
    document.addEventListener('DOMContentLoaded', function () {
    
    
        //==============================NAVIGATION BAR=============================
        themeMode()
        //=========================================================================


        //================================TRANG CHỦ================================
        scrollAnimation()
        foodModal()
        filterAndSearch()
        //=========================================================================
    

        //===========================TRANG CHỦ & CHATBOT===========================
        mapModal()
        //=========================================================================
    

        //=================================CHATBOT=================================
        chatBot()
        uploadImageFeature()
        //=========================================================================

    });
}

main()