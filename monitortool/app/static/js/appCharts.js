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

dataLine = []
dataBar = []
labelBar = []

var ctxLine, ctxBar, line, bar;

var canvas = document.getElementById('chart').getContext('2d');

function renderLineChart(){
    let data = {
        // labels: labels,
        datasets: [
        {
            label: 'Camera2',
            data: dataLine,
            fill: true,
            tension: 0.8
        },
    ]};

    line = new Chart(canvas, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            elements: {
                point: {
                    radius: 0
                },
                line: {
                    borderWidth: 1.5
                }
            },
            hover: {
                mode: null
            },
            tooltips: {
                enabled: false
            },
            scales: {
                yAxes: [{
                    gridLines: {
                        display: true 
                    },
                    ticks: {
                        beginAtZero: true,
                        fontSize: 13,
                        fontColor: 'whitesmoke'
                    }
                }],
                xAxes: [{
                    type: 'time',
                    gridLines: {
                        display: false 
                    },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 20,
                        fontSize: 13,
                        fontColor: 'whitesmoke'
                    }
                }]
            },
            legend: {
                position: 'right',
                labels: {
                    fontColor: 'whitesmoke'
                }
            },
            plugins: {
                colorschemes: {
                    scheme: 'tableau.SuperfishelStone10'
                },

            }
        }
    });
}

function renderBarChart(){

    let data = {
        labels: labelBar,
        datasets: [
        {
            data: dataBar,
            fill: true,
            tension: 0.8
        },
    ]};

    bar = new Chart(canvas, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            elements: {

            },
            scales: {
                y: {
                    beginAtZero: true
                },
                yAxes: [{
                    gridLines: {
                        display: true 
                    },
                    ticks: {
                        fontSize: 13,
                        fontColor: 'whitesmoke'
                    }
                }],
                xAxes: [{
                    gridLines: {
                        display: false 
                    },
                    ticks: {
                        fontSize: 13,
                        fontColor: 'whitesmoke'
                    }
                }]
            },
            legend: {
                display: false,
                position: 'right',
                labels: {
                    fontColor: 'whitesmoke'
                }
            },
            plugins: {
                colorschemes: {
                    scheme: 'tableau.SuperfishelStone10'
                },

            }
        }
    });
}

async function getAllData(){
    dataLine = await getData('line');
    let d = await getData('bar');
    for(let data of d){
        labelBar.push(data.name);
        dataBar.push(data.median);
    }
}

window.onload = function() {

    getAllData().then(() => {
        renderLineChart();
    })

    //$("#line").show();
}

$("#barChartBtn").click(e => {

    //$("#line").hide();
    
    line.destroy()
    renderBarChart();

    $("#barChartBtn").addClass("btn-light").removeClass("btn-outline-light");
    $("#lineChartBtn").addClass("btn-outline-light").removeClass("btn-light");

    // $("#bar").show();
    // renderBarChart();
});

$("#lineChartBtn").click(e => {

    bar.destroy()
    renderLineChart();

    $("#barChartBtn").removeClass("btn-light").addClass("btn-outline-light");
    $("#lineChartBtn").removeClass("btn-outline-light").addClass("btn-light");

});
