async function getData(param){
    var res = await fetch('/api/data/' + param);
    if (res.status != 200){
        return null;
    }
    let jsonresponse = await res.json();
    return jsonresponse; 
}

function getRandomColor() {
  var letters = '0123456789ABCDEF';
  var color = '#';
  for (var i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
}

function getRandomColorsList(count){
    col = []
    for(let i=0; i<count; i++){
        col.push(getRandomColor())
    }
    return col
}

window.onload = function() {
    getData('line').then(d => {
        if(!d){
            console.log("Data unavailable");
            return;
        }

		if(d.msg === "waiting"){
			console.log("Waiting for data to be avilable");
			return;
		}

        new Morris.Line({ // or line?
            element: 'chartContainer',
            pointSize: 0,
            data: d,
            dataLabels: false,
            xkey: 'x',
            ykeys: ['y'],
            labels: ['pm2.5 '],
            gridTextColor: 'whitesmoke',
            hideHover: 'always',
            gridTextSize: 15,
            resize: true,
            ymax: 400
        });
    });

    getData('bar').then(d => {
        if(!d){
            console.log("Data unavailable");
            return;
        }

		if(d.msg === "waiting"){
			console.log("Waiting for data to be avilable");
			return;
		}

        console.log(d);

        new Morris.Bar({ // or line?
            element: 'chartContainerBar',
            pointSize: 0,
            data: d,
            dataLabels: false,
            xkey: 'name',
            ykeys: ['median'],
            barColors: getRandomColorsList(d.length),
            // labels: ['pm2.5 '],
            gridTextColor: 'whitesmoke',
            // hideHover: 'always',
            gridTextSize: 15,
            resize: true,
            ymax: 400
        });
    });
}
