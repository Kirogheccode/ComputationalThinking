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
    var foodModal = document.getElementById('foodModal');
    if (foodModal) {
        foodModal.addEventListener('show.bs.modal', function (event) {
            var card = event.relatedTarget;
            if (!card) return;

            var name = card.getAttribute('data-name') || 'Không tên';
            var location = card.getAttribute('data-location') || '-';
            var rating = card.getAttribute('data-rating') || '-';
            var image = card.getAttribute('data-image') || '/static/images/placeholder-food.jpg';

            foodModal.querySelector('#modalFoodName').textContent = name;
            foodModal.querySelector('#modalFoodImage').src = image;
            foodModal.querySelector('#modalFoodLocation').textContent = location;
            foodModal.querySelector('#modalFoodRating').textContent = rating;

            foodModal.querySelector('#openMapBtn').href =
                `/map?name=${encodeURIComponent(name)}&location=${encodeURIComponent(location)}`;
        });
    }
}

// --- Hàm lọc, chỉ redirect khi Enter ---
window.applyFilters = function() {
    const area = document.getElementById('areaSelect').value;
    const q = document.getElementById('searchInput').value.trim();
    const params = new URLSearchParams({ area: area, q: q, page: 1 });
    window.location.href = "?" + params.toString();
};

// --- Hàm xóa filter nhưng không redirect ngay ---
window.clearFilters = function() {
    document.getElementById('areaSelect').value = 'all';
    document.getElementById('searchInput').value = '';
    applyFilters();
};

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

async function sendText(messageText){
    isProcess = true;
    const imageBtn = document.getElementById('imageInputBtn');
    const imageInput = document.getElementById('imageInput');
    const previewWrapper = document.getElementById('imagePreviewWrapper')
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('userInput');


    // Display user message
    displayUserMessage(messageText, chatWindow)

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
    const userInput = document.getElementById('userInput');

    if (userInput) {
        userInput.value = '';
    }

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

    previewImg.src = '';
    previewWrapper.classList.add('d-none');
    imageInput.value = '';
    
    displayUserMessage(text,chatWindow);
    if (userInput) {
        userInput.value = '';
    }

    // 2. Tạo loading bubble cho bot
    createLoadingBubble(chatWindow);
   
    // 3.1. Gửi ảnh lên backend (nếu có API) để nhận diện
    let botText1 = "";
    let food_predict = "";
    try {
        const formData = new FormData();
        formData.append("image", uploadedImage);

        const response = await fetch('/api/predict', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        botText1 = data.message;
        food_predict = data.food_name;
    } catch (err) {
        console.error("Lỗi khi gửi ảnh:", err);
        botText1 = "Xin lỗi, hệ thống gặp sự cố khi gửi ảnh.";
    }
    
    // 3.2. Gửi câu prompt lên API để xử lý và trả lời
    let botText2 = "";
    let messageText = (food_predict || '') + " " + (text || '');
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
        botText2 = data.reply;

        // RẤT QUAN TRỌNG: Thay thế ký tự xuống dòng (\n) bằng thẻ <br>
        // để chúng hiển thị đúng trong HTML
        botText2 = botText2.replace(/\n/g, '<br>');
        const container = document.getElementById("carousel");
        renderFoodCards(container, data.food_data);

    }
    catch (err) {
        console.error("Lỗi khi gọi API:", err);
        botText2 = "Xin lỗi, hệ thống đang gặp sự cố. Bạn vui lòng thử lại sau.";
    }
    // 4. Xoá loading bubble
    removeLoadingBubble();
    let botText = botText1 + "<br>" + botText2;
    // 5. Hiển thị tin nhắn trả lời từ bot
    displayBotMessage(botText, chatWindow);

    // 6. Reset preview và input
    uploadedImage = null;
    isProcess = false;
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
    const i18nEl = document.getElementById("sendMessageBtn");
    if (!i18nEl) return;

    // ✅ Lấy text đa ngôn ngữ giống themeMode()
    const textProcessing = i18nEl.dataset.processing;
    const textInputRequired = i18nEl.dataset.inputRequired;

    if (isProcess) {
        showNotification(textProcessing);
        return;
    }

    if (text === "") {
        showNotification(textInputRequired);
        return;
    }

    if (uploadedImage && text !== "") {
        await sendImage(text);
        return;
    }

    if (text !== "") {
        await sendText(text);
        return;
    }
}

function chatBot() {
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const userInput = document.getElementById('userInput');
    const chatWindow = document.getElementById('chat-window');

    if (!sendMessageBtn || !userInput || !chatWindow) {
        console.log("chatBot() skipped → elements not found");
        return;
    }

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
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const body = document.body;

    if (!themeToggleBtn) return;

    // Lấy text đa ngôn ngữ từ HTML
    const textDark = themeToggleBtn.dataset.dark;
    const textLight = themeToggleBtn.dataset.light;

    
    // === Theme initialization ===
    const savedTheme = localStorage.getItem("theme");

    if (savedTheme === "dark") {
        body.classList.add("dark");
        themeToggleBtn.textContent = "🌙 " + textDark;
    } else {
        body.classList.remove("dark");
        themeToggleBtn.textContent = "🌞 " + textLight;
    }

    // === Click toggle ===
    themeToggleBtn.addEventListener("click", () => {
        const isDark = body.classList.toggle("dark");
        themeToggleBtn.textContent = isDark
            ? "🌙 " + textDark
            : "🌞 " + textLight;

        localStorage.setItem("theme", isDark ? "dark" : "light");

        if (window.AOS) setTimeout(() => AOS.refresh(), 350);
    });
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
            <p class="food-location"><b>Địa chỉ</b>: ${food.Address}</p>
            <p class="food-rating"><b>Đánh giá</b>: ${food.Rating} ⭐</p>
            <p class = "food-budget"><b>Mức giá</b>: ${food.Budget} </p>
            <p class="food-description"><b>Mô tả<b>: ${food.Description}</p>
            <p class="food-distance"><b>Khoảng cách</b>: ${food.distance_km} km</p>
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

    if (!imageBtn || !imageInput || !previewWrapper) {
        console.log("uploadImageFeature() skipped → elements not found");
        return;
    }

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

document.addEventListener("DOMContentLoaded", function() {
    
    // Lấy tất cả nút tim
    const favoriteButtons = document.querySelectorAll('.btn-favorite');

    favoriteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault(); 

            const placeId = this.getAttribute('data-place-id');
            const placeName = this.getAttribute('data-place-name');
            const icon = this.querySelector('i'); // Icon trái tim

            fetch('/favorite/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    place_id: placeId,
                    place_name: placeName
                })
            })
            .then(response => {
                // TRƯỜNG HỢP 1: CHƯA ĐĂNG NHẬP (Lỗi 401)
                if (response.status === 401) {
                    return response.json().then(data => {
                        // Hiện thông báo yêu cầu
                        alert(data.message); 
                        // Chuyển hướng sang trang đăng nhập
                        window.location.href = "/login"; 
                    });
                }
                return response.json();
            })
            .then(data => {
                // TRƯỜNG HỢP 2: THÀNH CÔNG
                if (data && data.status === 'success') {
                    // Chỉ đổi màu icon, KHÔNG hiện alert nữa
                    if(icon) {
                        icon.classList.remove('far'); // Xóa tim rỗng
                        icon.classList.add('fas', 'text-danger'); // Thêm tim đặc màu đỏ
                    }
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });
});

function main()
{
    console.log("Main() is running!");
    document.addEventListener('DOMContentLoaded', function () {
        //==============================NAVIGATION BAR=============================
        themeMode()
        //=========================================================================

        //================================TRANG CHỦ================================
        scrollAnimation()
        foodModal()
        //=========================================================================

        //===========================TRANG CHỦ & CHATBOT===========================
        mapModal()
        //=========================================================================

        //=================================CHATBOT=================================
        chatBot()
        uploadImageFeature()
        //=========================================================================
        
        console.log("Filter JS loaded!");

        const areaSelect = document.getElementById("areaSelect");
        const searchInput = document.getElementById("searchInput");
        const clearBtn = document.getElementById("clearFilters");

        // === Apply Filters ===
        function applyFilters() {
            const area = areaSelect.value;
            const q = searchInput.value.trim();

            const params = new URLSearchParams({
                area: area,
                q: q,
                page: 1
            });

            console.log("Redirect to:", "?" + params.toString());
            window.location.href = "?" + params.toString();
        }

        // ===== Gắn event nếu các phần tử tồn tại =====
        if (areaSelect) {
            areaSelect.addEventListener("change", applyFilters);
        }

        if (searchInput) {
            searchInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    applyFilters();
                }
            });
        }

        if (clearBtn) {
            clearBtn.addEventListener("click", clearFilters);
        }
    });
}

main()