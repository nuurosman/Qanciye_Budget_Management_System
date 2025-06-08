document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const data = {
            email: document.getElementById("email").value,
            password: document.getElementById("password").value,
            user_type: document.getElementById("role").value,
        };

        try {
            const response = await fetch("/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            const errorMessage = document.getElementById("errorMessage");

            if (result.success) {
                errorMessage.style.display = "none";
                window.location.href = result.redirect_url;
            } else {
                errorMessage.style.display = "block";
                errorMessage.textContent = result.message;
            }
        } catch (error) {
            console.error("Login Error:", error);
        }
    });
});


function show_password(){
    const passwordfield=document.getElementById('password');
    const passwordIcon=document.getElementById('passwordIcon');

    if(passwordfield.type ==='password'){
        passwordfield.type='text';
        passwordIcon.classList.remove('bi bi-eye-fill');
        passwordIcon.classList.add('bi-eye-slash-fill');
    }
    else{
        passwordfield.type='password';
        passwordIcon.classList.remove('bi-eye-slash-fill')
        passwordfield.classList.add('bi bi-eye-fill')
    }

    }


// document.addEventListener("DOMContentLoaded", () => {
//     const loginForm = document.getElementById("loginForm");

//     loginForm.addEventListener("submit", async (event) => {
//         event.preventDefault();

//         const data = {
//             email: document.getElementById("email").value,
//             password: document.getElementById("password").value,
//             user_type: document.getElementById("role").value,
//         };

//         try {
//             const response = await fetch("/login", {
//                 method: "POST",
//                 headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify(data),
//             });

//             const result = await response.json();

//             if (result.success) {
//                 window.location.href = result.redirect_url;
//             } else {
//                 const errorMessage = document.getElementById("errorMessage");
//                 errorMessage.style.display = "block";
//                 errorMessage.textContent = result.message;
//             }
//         } catch (error) {
//             console.error("Login Error:", error);
//         }
//     });
// });
