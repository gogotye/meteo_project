document.addEventListener("DOMContentLoaded", function () {
    const input = document.querySelector("#city-input");
    const endpoint = input.dataset.autocompleteUrl;
    const hiddenSelection = document.querySelector("#city-selection");
    const form = document.querySelector("#search-form");

    const awesomplete = new Awesomplete(input, {
        minChars: 2,
        maxItems: 7,
        autoFirst: true,
        sort: false,
    });

    awesomplete.replace = function (suggestion) {
        input.value = suggestion.label || suggestion.value || "";
    };

    let timeout = null;

    function clearSelection() {
        hiddenSelection.value = "";
    }

    input.addEventListener("input", function () {
        clearTimeout(timeout);
        clearSelection();

        const query = input.value.trim();
        if (query.length < 2) return;

        timeout = setTimeout(() => {
            const url = `${endpoint}?q=${encodeURIComponent(query)}`;
            console.log("Запрос к:", url);
            fetch(url)
                .then((response) => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then((data) => {
                    // ожидаем от сервера массив объектов с полями
                    const suggestions = data.map((item) => {
                        const admin = item.admin1 ? `, рег. ${item.admin1}` : "";
                        const label = `гор. ${item.name}${admin}, стр. ${item.country} (${item.country_code})`;

                        const payload = {
                            city: item.name,
                            country: item.country,
                            country_code: item.country_code,
                            lat: item.latitude,
                            lon: item.longitude,
                            admin: item.admin1,
                        };
                        return {
                            label,
                            value: JSON.stringify(payload),
                        };
                    });

                    awesomplete.list = suggestions;
                })
                .catch((err) => console.error("Ошибка при получении городов:", err));
        }, 2000);
    });

    input.addEventListener("awesomplete-selectcomplete", function (evt) {
        const t = evt.text;
        const rawValue = typeof t === "object" && t !== null ? t.value : t;
        try {
            const parsed = typeof rawValue === "string" ? JSON.parse(rawValue) : rawValue;
            hiddenSelection.value = JSON.stringify(parsed);
        } catch (e) {
            console.warn("Не удалось распарсить значение подсказки:", e);
            hiddenSelection.value = "";
        }
    });

    form.addEventListener("submit", function () {
        if (hiddenSelection.value && input.value.trim().length < 2) {
            hiddenSelection.value = "";
        }
    });
});
