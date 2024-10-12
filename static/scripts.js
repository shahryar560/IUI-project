document.addEventListener("DOMContentLoaded", function() {
    const ctx = document.getElementById('dailySummaryChart').getContext('2d');
    fetch("/get_summary_data")
        .then(response => response.json())
        .then(data => {
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.dates,
                    datasets: [
                        {
                            label: 'Calorie Intake',
                            data: data.calorie_intake,
                            backgroundColor: '#ff6384'
                        },
                        {
                            label: 'Calories Burned',
                            data: data.calories_burned,
                            backgroundColor: '#36a2eb'
                        },
                        {
                            label: 'Water Intake (ml)',
                            data: data.water_intake,
                            backgroundColor: '#4bc0c0'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Amount'
                            }
                        }
                    }
                }
            });
        });

    // Apply saved accent color and theme
    const theme = "{{ user.theme }}";
    const fontSize = "{{ user.font_size }}";
    const accentColor = "{{ user.accent_color }}";

    document.body.setAttribute("data-theme", theme);
    document.body.setAttribute("data-font-size", fontSize);
    document.documentElement.style.setProperty('--accent-color', accentColor);

    console.log("Theme:", "{{ user.theme }}");
    console.log("Font Size:", "{{ user.font_size }}");
    console.log("Accent Color:", "{{ user.accent_color }}");

    const suggestionsBox = document.getElementById("suggestions");
    if (theme === "dark") {
        suggestionsBox.style.color = "#fff"; // Light text for dark theme
        suggestionsBox.style.backgroundColor = "#333"; // Dark background
    } else {
        suggestionsBox.style.color = "#333"; // Dark text for light theme
        suggestionsBox.style.backgroundColor = "#fff"; // Light background
    }

    function getHealthStatus() {
        fetch('/get_health_status')
            .then(response => response.json())
            .then(data => {
                document.getElementById('statusResponse').textContent = data.status;
            })
            .catch(error => console.error('Error fetching health status:', error));
    }
    

});
