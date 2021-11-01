// Relies on chart.js and users Line and Bar chart

// Gets data from the api
async function getData(param){
    var res = await fetch('/api/data/' + param);
    if (res.status != 200){
        return null;
    }
    let jsonresponse = await res.json();
    return jsonresponse; 
}

dataLine = []          // Points for line plot
dataBar = []           // points for bar plot
labelBar = []          // labels for bar plot

var ctxLine, ctxBar, line, bar;

// Gets the canvas from the HTML page
var canvas = document.getElementById('chart').getContext('2d');

// Renders the line chart on the canvas
function renderLineChart(){
    line = new Chart(canvas, {
        type: 'line',
        data: {
            datasets: dataLine
        },
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

// Renders the bar chart on the canvas
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

// Gets data for line and bar chart
async function getAllData(){
    let dLine = await getData('line');
    for(let data of dLine){
        dataLine.push({
            label: data.name,
            data: data.points,
            fill: true,
            tension: 0.8
        })
    }
    let dBar = await getData('bar');
    for(let data of dBar){
        labelBar.push(data.name);
        dataBar.push(data.median);
    }
}

// On load gets all data and shows line chart
window.onload = function() {

    getAllData().then(() => {
        renderLineChart();
    })

}

// When the bar chart button is clicked, changes chart
$("#barChartBtn").click(e => {
    
    line.destroy()
    renderBarChart();

    $("#barChartBtn").addClass("btn-light").removeClass("btn-outline-light");
    $("#lineChartBtn").addClass("btn-outline-light").removeClass("btn-light");

});

// When the line chart button is clicked, changes chart
$("#lineChartBtn").click(e => {

    bar.destroy()
    renderLineChart();

    $("#barChartBtn").removeClass("btn-light").addClass("btn-outline-light");
    $("#lineChartBtn").removeClass("btn-outline-light").addClass("btn-light");

});
