document.addEventListener("DOMContentLoaded", () => {
    const registrationForm = document.getElementById("registrationForm");

    registrationForm.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent default form submission

        // Gather form data
        const formData = new FormData(registrationForm);
        const data = Object.fromEntries(formData);

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
                alert(result.message);
                registrationForm.reset(); // Reset the form
            } else {
                alert("Error: " + result.message);
            }
        } catch (error) {
            console.error("Registration Error:", error);
            alert("An error occurred during registration.");
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
                alert("User updated successfully!");
                window.location.reload();
            } else {
                alert("Error: " + result.message);
            }
        } catch (error) {
            console.error("Edit Error:", error);
            alert("An error occurred while editing the user.");
        }
    });
});


