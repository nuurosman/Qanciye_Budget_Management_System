document.addEventListener("DOMContentLoaded", () => {
    const registrationForm = document.getElementById("registrationForm");

    // Toast configuration function (matching attendance toast)
    function configureToast() {
        return Swal.mixin({
            toast: true,
            position: 'top',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
            width: '380px',
            padding: '16px',
            background: '#fff',
            color: '#2c3e50',
            customClass: {
                timerProgressBar: 'swal2-timer-progress-bar-custom'
            },
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer)
                toast.addEventListener('mouseleave', Swal.resumeTimer)
            }
        });
    }

    registrationForm.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent default form submission

        // Gather form data
        const formData = new FormData(registrationForm);
        const data = Object.fromEntries(formData);

        const Toast = configureToast();

        try {
            const response = await fetch("/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (result.success) {
                Toast.fire({
                    icon: 'success',
                    iconColor: '#27ae60',
                    title: `Registration Successful`,
                    html: `<div style="margin-top:8px;font-size:15px">${result.message || "User registered successfully!"}</div>`
                });
                registrationForm.reset(); // Reset the form
            } else {
                Toast.fire({
                    icon: 'error',
                    iconColor: '#e74c3c',
                    title: `Registration Failed`,
                    html: `<div style="margin-top:8px;font-size:15px">${result.message || "Registration failed."}</div>`
                });
            }
        } catch (error) {
            console.error("Registration Error:", error);
            Toast.fire({
                icon: 'error',
                iconColor: '#e74c3c',
                title: `System Error`,
                html: `<div style="margin-top:8px;font-size:15px">An error occurred during registration.</div>`
            });
        }
    });
});


// Handle the edit form submission dynamically
const editForms = document.querySelectorAll('[data-edit-user]');
editForms.forEach((form) => {
    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const userId = form.getAttribute('data-user-id');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);

        const Toast = configureToast();

        try {
            const response = await fetch(`/edit/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (result.success) {
                Toast.fire({
                    icon: 'success',
                    iconColor: '#27ae60',
                    title: `User Updated`,
                    html: `<div style="margin-top:8px;font-size:15px">User updated successfully!</div>`
                });
                setTimeout(() => window.location.reload(), 1500);
            } else {
                Toast.fire({
                    icon: 'error',
                    iconColor: '#e74c3c',
                    title: `Update Failed`,
                    html: `<div style="margin-top:8px;font-size:15px">${result.message || "Update failed."}</div>`
                });
            }
        } catch (error) {
            console.error("Edit Error:", error);
            Toast.fire({
                icon: 'error',
                iconColor: '#e74c3c',
                title: `System Error`,
                html: `<div style="margin-top:8px;font-size:15px">An error occurred while editing the user.</div>`
            });
        }
    });
});


