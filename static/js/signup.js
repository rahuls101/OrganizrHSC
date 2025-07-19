document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const firstName = document.getElementById("first-name");
    const lastName = document.getElementById("last-name");
    const email = document.getElementById("email");
    const password = document.getElementById("password");
    const confirmPassword = document.getElementById("confirm-password");
    const terms = document.getElementById("terms");
    const submitButton = document.getElementById("submit-button");

    // Error elements
    const errors = {
        "first-name": document.getElementById("first-name-error"),
        "last-name": document.getElementById("last-name-error"),
        "email": document.getElementById("email-error"),
        "password": document.getElementById("password-error"),
        "confirm-password": document.getElementById("confirm-password-error"),
        "terms": document.getElementById("terms-error")
    };

    // Validation state
    const valid = {
        "first-name": false,
        "last-name": false,
        "email": false,
        "password": false,
        "confirm-password": false,
        "terms": false
    };

    function showError(input, errorEl, msg) {
        input.classList.add("border-red-500", "focus:ring-red-500", "focus:border-red-500");
        errorEl.innerHTML = msg;
        errorEl.classList.remove("hidden");
    }

    function hideError(input, errorEl) {
        input.classList.remove("border-red-500", "focus:ring-red-500", "focus:border-red-500");
        errorEl.classList.add("hidden");
    }

    function hasValidNameCharacters(name) {
        return /^[A-Za-z-]{1,25}$/.test(name);
    }

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    function validatePassword(pwd) {
        const errors = [];
        if (pwd.length < 8) errors.push("at least 8 characters");
        if (!/[a-z]/.test(pwd)) errors.push("a lowercase letter");
        if (!/[A-Z]/.test(pwd)) errors.push("an uppercase letter");
        if (!/[0-9]/.test(pwd)) errors.push("a number");
        return errors;
    }

    function updateSubmitState() {
        const allValid = Object.values(valid).every(Boolean);
        submitButton.disabled = !allValid;
    }

    // Debounce helper
    function debounce(func, delay) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                func(...args);
            }, delay);
        };
    }

    firstName.addEventListener("input", () => {
        const value = firstName.value

        if (value.length > 25) {
            showError(firstName, errors["first-name"], "Must be 25 characters or fewer");
            valid["first-name"] = false;
        } else if (!hasValidNameCharacters(value)) {
            showError(firstName, errors["first-name"], "Please enter a valid first name.");
            valid["first-name"] = false;
        } else {
            hideError(firstName, errors["first-name"]);
            valid["first-name"] = true;
        }

        updateSubmitState();
    });

    lastName.addEventListener("input", () => {
        const value = lastName.value

        if (value.length > 25) {
            showError(lastName, errors["last-name"], "Must be 25 characters or fewer");
            valid["last-name"] = false;
        } else if (!hasValidNameCharacters(value)) {
            showError(lastName, errors["last-name"], "Please enter a valid last name.");
            valid["last-name"] = false;
        } else {
            hideError(lastName, errors["last-name"]);
            valid["last-name"] = true;
        }
        updateSubmitState();
    });


    // Debounced backend check
    const debouncedCheckEmailBackend = debounce((emailValue) => {
        fetch("/check_email", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email: emailValue
                }),
            })
            .then((response) => response.json())
            .then((data) => {
                if (data.exists) {
                    showError(email, errors["email"], `Email already in use. <a href="${loginUrl}" class="text-blue-700 underline hover:text-blue-900">Login</a>?`);
                    valid["email"] = false;
                } else {
                    hideError(email, errors["email"]);
                    valid["email"] = true;
                }
                updateSubmitState();
            });
    }, 500);

    // Listener that always runs
    email.addEventListener("input", () => {
        const emailValue = email.value;

        if (!isValidEmail(emailValue)) {
            // ran on every keystroke
            showError(email, errors["email"], "Please enter a valid email address (yourname@domain.com)");
            valid["email"] = false;
            updateSubmitState();
        } else {
            // Hide invalid format message immediately
            hideError(email, errors["email"]);

            // backend check, but debounced
            debouncedCheckEmailBackend(emailValue);
        }
    });

    password.addEventListener("input", () => {
        const pwdErrors = validatePassword(password.value);
        if (pwdErrors.length === 0) {
            hideError(password, errors["password"]);
            valid["password"] = true;
        } else {
            showError(password, errors["password"], "Password must include: " + pwdErrors.join(", ") + ".");
            valid["password"] = false;
        }

        // Confirm password recheck
        if (confirmPassword.value.length > 0) {
            if (confirmPassword.value === password.value) {
                hideError(confirmPassword, errors["confirm-password"]);
                valid["confirm-password"] = true;
            } else {
                showError(confirmPassword, errors["confirm-password"], "Passwords do not match.");
                valid["confirm-password"] = false;
            }
        }

        updateSubmitState();
    });

    confirmPassword.addEventListener("input", () => {
        if (confirmPassword.value === password.value) {
            hideError(confirmPassword, errors["confirm-password"]);
            valid["confirm-password"] = true;
        } else {
            showError(confirmPassword, errors["confirm-password"], "Passwords do not match.");
            valid["confirm-password"] = false;
        }
        updateSubmitState();
    });

    terms.addEventListener("change", () => {
        if (terms.checked) {
            terms.classList.remove("border-red-500", "ring-red-500", "focus:ring-red-500");
            errors["terms"].classList.add("hidden");
            valid["terms"] = true;
        } else {
            terms.classList.add("border-red-500", "ring-red-500", "focus:ring-red-500");
            errors["terms"].classList.remove("hidden");
            valid["terms"] = false;
        }
        updateSubmitState();
    });
});