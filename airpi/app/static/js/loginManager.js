// Handles login form submission
$("#loginForm").submit(async (e) => {
    e.preventDefault();
    var form = document.querySelector("#loginForm");
    var username = form.querySelector('input[id="username"]').value;
    var password = form.querySelector('input[id="password"]').value;

    var msg = {
        username: username,
        password: password
    };

    let response = await fetch('/api/auth', {
        method: 'POST', 
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(msg),
    });

    let status = await response.status;

    if (status == 200){
        console.log("ok");
        window.location.replace("/");
    }else{
        alert("Not authorized");
    }
});