document.getElementById("resetPasswordForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const data = {
        email: document.getElementById("email").value,
        new_password: document.getElementById("newPassword").value,
        user_type: document.getElementById("role").value,
    };

    try {
        const response = await fetch("/reset_password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });

        const result = await response.json();
        alert(result.message);
    } catch (error) {
        console.error("Password reset error:", error);
    }
});

function togglePasswordVisibility() {
    const passwordField = document.getElementById('newPassword');
    const passwordIcon = document.getElementById('togglePasswordIcon');

    if (passwordField.type === 'password') {
        passwordField.type = 'text';
        passwordIcon.classList.remove('bi-eye-fill');
        passwordIcon.classList.add('bi-eye-slash-fill');
    } else {
        passwordField.type = 'password';
        passwordIcon.classList.remove('bi-eye-slash-fill');
        passwordIcon.classList.add('bi-eye-fill');
    }
}
