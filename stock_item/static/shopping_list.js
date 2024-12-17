document.addEventListener("DOMContentLoaded", function () {
    // 購入予定数の増減ボタン
    document.querySelectorAll(".increment").forEach(button => {
        button.addEventListener("click", function () {
            const input = this.previousElementSibling;
            input.value = parseInt(input.value || 0) + 1;
        });
    });

    document.querySelectorAll(".decrement").forEach(button => {
        button.addEventListener("click", function () {
            const input = this.nextElementSibling;
            input.value = Math.max(0, parseInt(input.value || 0) - 1); // 負の数を防ぐ
        });
    });
});
