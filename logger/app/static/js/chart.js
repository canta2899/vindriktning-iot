async function getData(){
    var res = await fetch('/api/data');
    if (res.status != 200){
        return null;
    }
    let jsonresponse = await res.json();
    return jsonresponse; 
}

window.onload = function() {
    getData().then(d => {
        if(!d){
            $("#chartContainer").html("Data unavailable");
            return;
        }
        $("#chartContainer").html("");
        // var chart = new CanvasJS.Chart("chartContainer", {
        //     animationEnabled: true,
        //     theme: "light2",
        //     title: {
        //         text: "Mannaggia"
        //     },
        //     axisX: {
        //         title: "Time",
        //         valueFormatString: "HH:s"
        //     },
        //     axisY: {
        //         title: "PM25",
        //         includeZero: true
        //     },
        //     data: [{
        //         type: "line",
        //         // type: "splineArea",
        //         color: "rgba(54,158,173,.7)",
        //         name: "Air quality",
        //         xValueType: "dateTime",
        //         connectNullData: true,
        //         dataPoints: data
        //     }]
        // });
        // chart.render();
        new Morris.Area({ // or line?
            element: 'chartContainer',
            data: d,
            xkey: 'x',
            ykeys: ['y'],
            labels: ['pm2.5 '],
            gridTextColor: 'blactk',
            gridTextSize: 15,
            resize: true,
            ymax: 200
        });
    });
}