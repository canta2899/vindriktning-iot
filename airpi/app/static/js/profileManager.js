// Handles updates of user's own profile

$("#userUpdate").submit(function(e){
    e.preventDefault();
    let form = $(this).serializeJSON();
    data = {
        username: form.username,
        newPassword: form.newpass1,
        reqPassword: form.reqpass,
    }

    $.ajax({
        method: 'PUT',
        url: '/api/me',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        credentials: 'same-origin',
        dataType: 'json',
        data: JSON.stringify(data),
        success: function(){
            window.location.replace("/");
        },
        error: function(xhr){
            var err = JSON.parse(xhr.responseText);
            alert("Update not valid: " + err);
        }  
    })
});