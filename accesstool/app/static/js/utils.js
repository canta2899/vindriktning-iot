async function getTokensFetch(){
    let r = await fetch('/api/tokens', {
        method: 'GET', 
        cache: 'no-cache',
        headers: {
        'Content-Type': 'application/json'
        },
    });
    
    let val = await r.json();
    return val;
}

function parseToken(t){
    if (t.chat_id === ''){
        t.chat_id = 'Not known';
    }

    if(t.expired){
        $("tbody").append("<tr class='yellow'><td scope='row'>" + t.username + "</td><td>" + t.chat_id + "</td><td>" + t.expires.split(".")[0] + "</td></tr>");
    }else{
        $("tbody").append("<tr><td scope='row'>" + t.username + "</td><td>" + t.chat_id + "</td><td>" + t.expires.split(".")[0] + "</td></tr>");
    }
}

function getTokens(){
    getTokensFetch().then(val => {
        $("tbody").html("");
        val.forEach(t => parseToken(t))
    })
}


$("#newTokenForm").submit(async (e) => {
    e.preventDefault();
    var form = document.querySelector("#newTokenForm");
    var username = form.querySelector('input[name="token_username"]').value;
    var duration = form.querySelector('input[name="token_duration"]').value;

    var msg = {
        username: username,
        duration: parseInt(duration)
    };

    let response = await fetch('/api/newtoken', {
        method: 'POST', 
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(msg),
    });

    let status = await response.status;

    if (status == 200){
        console.log("Added new token");
        getTokens();
    }else{
        alert("Unable to add new token");
    }
});

$("#delTokenForm").submit(async (e) => {
    e.preventDefault();
    var form = document.querySelector("#delTokenForm");
    var username = form.querySelector('input[name="token_username"]').value;

    var msg = {
        username: username,
    };

    let response = await fetch('/api/deltoken', {
        method: 'POST', 
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(msg),
    });

    let status = await response.status;

    if (status == 200){
        console.log("Deleted token");
        getTokens();
    }else{
        alert("Authorization not found for that user");
    }
});

$("#tokensbtn").click((e) => {
    getTokens()
});
