// import {sendQueryToGemini} from './gemini.js'

const foodData = [
    {
        Name: "Phở Bò Gánh",
        Address: "123 Đường ABC, Hà Nội",
        Description: "Phở truyền thống Việt Nam, nước dùng đậm đà.",
        Image: "images/pho_bo.jpg",
        OpeningTime: "Mo-Su 10:00-21:00",
        Cuisine: "vietnamese"
    },
    {
        Name: "Bún Chả Hương Liên",
        Address: "24 Lê Văn Hưu, Hà Nội",
        Description: "Bún chả thơm ngon với chả nướng và nước chấm đậm vị.",
        Image: "images/bun.jpg",
        OpeningTime: "Mo-Su 10:00-21:00",
        Cuisine: "vietnamese"
    },
    {
        Name: "Cơm Tấm Sài Gòn",
        Address: "56 Nguyễn Trãi, TP.HCM",
        Description: "Cơm tấm với sườn nướng và trứng ốp la hấp dẫn.",
        Image: "images/com_tam.jpg",
        OpeningTime: "Mo-Su 10:00-21:00",
        Cuisine: "vietnamese"
    },
    {
        Name: "Bánh Mì Phượng",
        Address: "2B Phan Chu Trinh, Đà Nẵng",
        Description: "Bánh mì giòn tan, pate thơm ngon và thịt nướng đậm vị.",
        Image: "images/banh_mi_thit.jpg",
        OpeningTime: "Mo-Su 10:00-21:00",
        Cuisine: "vietnamese"
    },
    {
        Name: "Chè Hẻm",
        Address: "37 Lê Thánh Tôn, TP.HCM",
        Description: "Các loại chè truyền thống, ngọt dịu và thanh mát.",
        Image: "images/che.jpg",
        OpeningTime: "Mo-Su 10:00-21:00",
        Cuisine: "vietnamese"
    }
];

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
function pauseCheck(track)
{
    const pauseBtn = document.querySelector('.pause');

    pauseBtn.addEventListener('click', () => {
        // Kiểm tra animation đang paused hay chưa
        const isPaused = track.classList.toggle('paused'); // toggle trả về true nếu vừa add class

        // Thay đổi iconto
        if (isPaused) 
        {
            // Nếu paused → hiển thị icon play
            pauseBtn.innerHTML = '<i class="fa-regular fa-square-caret-right"></i>';
        } else 
        {
            // Nếu đang chạy → hiển thị icon pause
            pauseBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
        }
    });
}
function fastCheck(track)
{
    const fastBtn = document.querySelector('.fast');

    let isFast = false; // trạng thái fast forward

    fastBtn.addEventListener('click', () => {
        isFast = !isFast; // toggle trạng thái

        if (isFast) 
        {
            // tua nhanh 1.5x → giảm duration xuống 2/3
            track.style.animationDuration = '5s'; // ví dụ gốc 10s / 1.5
            fastBtn.style.backgroundColor = 'rgba(255, 165, 0, 0.7)'; // highlight nút (tuỳ chọn)
        }
        else 
        {
            // trở về tốc độ bình thường
            track.style.animationDuration = '20s';
            fastBtn.style.backgroundColor = ''; // reset
        }
    });
}
function restartCheck()
{
    // === SỰ KIỆN NÚT RELOAD ===
    const reloadBtn = document.querySelector('.restart');
    reloadBtn.addEventListener("click", () => {
    updateFoodModal(foodData);
    });
}
function chatBot() {
    // --- Simple Chatbot UI Logic ---
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const userInput = document.getElementById('userInput');
    const chatWindow = document.getElementById('chat-window');

    if (sendMessageBtn && userInput && chatWindow) {
        sendMessageBtn.addEventListener('click', function () {
            sendMessage();
        });

        userInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    async function sendMessage() {
        const messageText = userInput.value.trim();
        if (messageText === '') return;

        // Display user message
        const userMessageDiv = document.createElement('div');
        userMessageDiv.classList.add('message', 'user-message');
        userMessageDiv.innerHTML = `<p>${messageText}</p>`;
        chatWindow.appendChild(userMessageDiv);
        userInput.value = '';
        chatWindow.scrollTop = chatWindow.scrollHeight;

        // Create loading bubble
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('message', 'bot-message', 'loading-message');
        loadingDiv.innerHTML = `<p></p>`;
        chatWindow.appendChild(loadingDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;

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
            // botText = data.reply;
            botText = "Đây là một vài đề xuất phù hợp với yêu cầu của bạn!"


            // RẤT QUAN TRỌNG: Thay thế ký tự xuống dòng (\n) bằng thẻ <br>
            // để chúng hiển thị đúng trong HTML
            // botText = botText.replace(/\n/g, '<br>');
            updateFoodModal(data.food_data);

        }
        catch (err) {
            console.error("Lỗi khi gọi API:", err);
            botText = "Xin lỗi, hệ thống đang gặp sự cố. Bạn vui lòng thử lại sau.";
        }

        // Remove loading bubble
        loadingDiv.remove();

        // Display bot response
        const botMessageDiv = document.createElement('div');
        botMessageDiv.classList.add('message', 'bot-message', 'd-flex', 'align-items-start');
        botMessageDiv.innerHTML = `
            <img src="/static/images/jane.jpg" class="bot-avatar" alt="Bot Avatar">
            <p>${botText}</p>
        `;
        chatWindow.appendChild(botMessageDiv);

        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

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
    data.forEach(food => {
        const card = document.createElement('div');
        card.classList.add('card-food');
        card.innerHTML = `
            <img src="/static/${food.Image}" alt="${food.Name}">
            <div class="food-info">
                <h5 class="food-name">${food.Name}</h5>
                <p class="food-location">Địa chỉ: ${food.Address}</p>
                <p class="food-description">${food.Description}</p>
                <p class="food-open-time">Giờ mở cửa: ${food.OpeningTime}</p>
                <p class="cuisine">Ẩm thực: ${food.Cuisine}</p>
            </div>
            <button class="location-btn location-dot"
                    title="Xem trên bản đồ"
                    data-bs-toggle="modal" 
                    data-bs-target="#mapModal"
                    data-name="${food.Name}"
                    data-description="${food.Description}"
                    data-location="${food.Address}"
                    data-image="/static/${food.Image}">
                <i class="fa-solid fa-location-dot"></i>
            </button>
        `;
        container.appendChild(card);
    });
}
function updateFoodModal(dataArray) {
    // Lấy tất cả thẻ card hiện có trong modal
    const cards = document.querySelectorAll('.card-food');

    if (!cards || cards.length === 0) {
        console.warn("Không có thẻ card-food nào để cập nhật.");
        return;
    }

    if (!dataArray || dataArray.length === 0) {
        console.warn("Dữ liệu cập nhật rỗng, không thể ghi đè modal.");
        return;
    }
    // Nếu số dữ liệu ít hơn số card → lặp lại dữ liệu cho đủ
    const totalCards = cards.length;
    const totalData = dataArray.length;
    const repeatedData = [];

    for (let i = 0; i < totalCards; i++) {
        repeatedData.push(dataArray[i % totalData]);
    }

    // Ghi đè nội dung từng card theo dữ liệu mới
    cards.forEach((card, index) => {
        const food = repeatedData[index];
        const img = card.querySelector('img');
        const name = card.querySelector('.food-name');
        const location = card.querySelector('.food-location');
        const description = card.querySelector('.food-description');
        const openTime = card.querySelector('.food-open-time');
        const cuisine = card.querySelector('.cuisine');
        const button = card.querySelector('.location-btn');

        // Xử lý ảnh: nếu food.image không tồn tại, dùng ảnh mặc định
        const imageSrc = food && food.Image ? `/static/${food.Image}` : '/static/images/default_food.jpg';

        if (img) {
            img.src = imageSrc;
            img.alt = food.Name || "Ẩm thực";
        }
        if (name) name.textContent = food.Name || "Tên chưa có";
        if (location) location.textContent = `Địa chỉ: ${food.Address || "Chưa có địa chỉ"}`;
        if (description) description.textContent = food.Description || "Không có mô tả";
        if (openTime) openTime.textContent = `Giờ mở cửa: ${food.OpeningTime || "Chưa có giờ mở cửa"}`;
        if (cuisine) cuisine.textContent = `Ẩm thực: ${food.Cuisine || "Chưa rõ"}`;

        if (button) {
            button.dataset.name = food.Name || "";
            button.dataset.description = food.Description || "";
            button.dataset.location = food.Address || "";
            button.dataset.image = imageSrc;
        }
    });


    console.log(` Đã cập nhật ${totalCards} card với ${totalData} dữ liệu (ghi đè lặp lại nếu thiếu).`);
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
        const track = document.getElementById('food-track');
        if (track)
        {
            renderFoodCards(track, foodData);
            pauseCheck(track)
            fastCheck(track)
            restartCheck()
        }
        //=========================================================================

    });
}

main()





