// script.js

const windowLocation = window.location;
const windowLocationArr = windowLocation.href.toString().split("/");
const user_email = windowLocationArr[windowLocationArr.length - 1];

// Define an array to store user calendars
let user_calendars = [];
// Define an array to store all calendars
let all_calendars = [];

// Define an array to store events
let events = [];

// Function to load existing events from db
async function load() {
    let user = windowLocationArr[0] + '//' + windowLocationArr[2] + '/api/users/' + user_email;
    user = await fetch(user);
    user = await user.json();

    let db_calendars = windowLocationArr[0] + '//' + windowLocationArr[2] + '/api/calendars'
    db_calendars = await fetch(db_calendars);
    db_calendars = await db_calendars.json();

    user_calendars = [];
    all_calendars = [];
    events = [];

    for (let i = 0; i < db_calendars.length; i++) {
        let c = db_calendars[i];
        all_calendars.push(
            {
                id: c["calendar_id"], 
                name: c["name"],
                events: c["events"],
                organization: c["organization"],
                season: c["season"]
            }
        );
        if (user["calendars"].includes(c["calendar_id"])) {
            user_calendars.push(
                {
                    id: c["calendar_id"], 
                    name: c["name"],
                    events: c["events"],
                    organization: c["organization"],
                    season: c["season"]
                }
            );
            calendar_events = c["events"];
            for (let j = 0; j < calendar_events.length; j++) {
                let event = calendar_events[j];
                events.push(
                    {
                        id: event["event_id"], 
                        date: event["date"],
                        title: event["title"],
                        description: event["description"],
                        calendar_id: event["calendar_id"]
                    }
                );
            }
        }
    }
    showCalendar(currentMonth, currentYear);
    displayCalendars();
}
load();

// Function to display user calendars
function displayCalendars() {
    // display user calendars (unchanged)
    let myCalendarList = document.getElementById("myCalendarList");
    myCalendarList.innerHTML = "";
    for (let i = 0; i < user_calendars.length; i++) {
        let calendar = user_calendars[i];
        let listItem = document.createElement("li");
        listItem.innerHTML =
            `- <strong>${calendar.name} - ${calendar.organization}</strong>`

        // Add a subscribe button for each reminder item
        let deleteButton =
            document.createElement("button");
        deleteButton.className = "delete-event";
        deleteButton.textContent = "Unsubscribe";
        deleteButton.onclick = function () {
            unsubscribe(user_email, calendar.id);
        };
        listItem.appendChild(deleteButton);
        myCalendarList.appendChild(listItem);
    }

    // Group calendars by organization
    const calendarsByOrg = {};
    for (let i = 0; i < all_calendars.length; i++) {
        const calendar = all_calendars[i];
        const org = calendar.organization;
        
        if (!calendarsByOrg[org]) {
            calendarsByOrg[org] = [];
        }
        calendarsByOrg[org].push(calendar);
    }
    
    // Display organizations and their teams
    const organizationSections = document.getElementById("organizationSections");
    organizationSections.innerHTML = "";
    
    for (const org in calendarsByOrg) {
        // Create organization section
        const orgSection = document.createElement("div");
        orgSection.className = "organization-section";
        
        // Create organization header
        const orgHeader = document.createElement("div");
        orgHeader.className = "organization-header";
        orgHeader.innerHTML = `<strong>${org}</strong><span class="toggle-icon">+</span>`;
        
        // Create teams container
        const teamsContainer = document.createElement("ul");
        teamsContainer.className = "organization-teams";
        
        // Add click event to toggle teams visibility
        orgHeader.addEventListener("click", function() {
            teamsContainer.classList.toggle("active");
            const toggleIcon = this.querySelector(".toggle-icon");
            toggleIcon.textContent = teamsContainer.classList.contains("active") ? "-" : "+";
        });
        
        // Add teams to this organization in alphabetical order
        const sortedCalendars = [...calendarsByOrg[org]].sort((a, b) => 
            a.name.localeCompare(b.name)
        );
        
        for (let i = 0; i < sortedCalendars.length; i++) {
            const calendar = sortedCalendars[i];
            const teamItem = document.createElement("li");
            teamItem.className = "team-item";
            teamItem.innerHTML = `<span>${calendar.name}</span>`;
            
            // Add subscribe button
            const subscribeBtn = document.createElement("button");
            subscribeBtn.className = "delete-event";
            
            // Check if user is already subscribed
            let subscribed = false;
            for (let j = 0; j < user_calendars.length; j++) {
            if (user_calendars[j].id === calendar.id) {
                subscribed = true;
                break;
            }
            }
            
            if (subscribed) {
            subscribeBtn.textContent = "Subscribed!";
            subscribeBtn.style.backgroundColor = "gray";
            } else {
            subscribeBtn.textContent = "Subscribe";
            }
            
            subscribeBtn.onclick = function() {
            subscribe(user_email, calendar.id);
            };
            
            teamItem.appendChild(subscribeBtn);
            teamsContainer.appendChild(teamItem);
        }
        
        // Assemble the organization section
        orgSection.appendChild(orgHeader);
        orgSection.appendChild(teamsContainer);
        organizationSections.appendChild(orgSection);
    }
}

// Function to subscribe to a calendar
async function subscribe(user_email, calendar_id) {
    let url = windowLocationArr[0] + '//' + windowLocationArr[2] + '/api/subscribe'
    let data = {
        user_email: user_email,
        calendar_id: calendar_id
    }
    await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    load();
}

// Function to unsubscribe to a calendar
async function unsubscribe(user_email, calendar_id) {
    let url = windowLocationArr[0] + '//' + windowLocationArr[2] + '/api/unsubscribe'
    let data = {
        user_email: user_email,
        calendar_id: calendar_id
    }
    await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    load();
}

async function sync() {
    let sync_button = document.getElementById("sync");

    // Store original width and set fixed width
    const originalWidth = sync_button.offsetWidth;
    sync_button.style.width = originalWidth + "px";
    sync_button.style.textAlign = "center";

    sync_button.innerText = "Sync-ing..."
    let url = windowLocationArr[0] + '//' + windowLocationArr[2] + '/google/sync'
    let data = {}
    for (let i = 0; i < user_calendars.length; i++) {
        let key = user_calendars[i]["name"] + " - " + user_calendars[i]["organization"];
        data[key] = []
        user_cal = user_calendars[i]["events"]
        for (let j = 0; j < user_cal.length; j++) {
            data[key].push(user_cal[j])
        }
    }
        
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    }).then(response => {
        if (response.ok) {
            console.log("response", response)
            sync_button.innerText = "Sync w/ GCal"
            return
        } else {
            throw new Error('Error in sync dashboard.js');
        }
    });

    // Animation for sync button
    let syncDots = 0;
    let syncInterval = setInterval(() => {
        if (sync_button.innerText.startsWith("Sync-ing")) {
            syncDots = (syncDots % 3) + 1;
            sync_button.innerText = "Sync-ing" + ".".repeat(syncDots);
        } else {
            clearInterval(syncInterval);
        }
    }, 1000);
    
}

// Function to generate a range of 
// years for the year select input
function generate_year_range(start, end) {
	let years = "";
	for (let year = start; year <= end; year++) {
		years += "<option value='" +
			year + "'>" + year + "</option>";
	}
	return years;
}

// Initialize date-related letiables
today = new Date();
currentMonth = today.getMonth();
currentYear = today.getFullYear();
selectYear = document.getElementById("year");
selectMonth = document.getElementById("month");

createYear = generate_year_range(1970, 2050);

document.getElementById("year").innerHTML = createYear;

let calendar = document.getElementById("calendar");

let months = [
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December"
];
let days = [
	"Sun", "Mon", "Tue", "Wed",
	"Thu", "Fri", "Sat"];

$dataHead = "<tr>";
for (dhead in days) {
	$dataHead += "<th data-days='" +
		days[dhead] + "'>" +
		days[dhead] + "</th>";
}
$dataHead += "</tr>";

document.getElementById("thead-month").innerHTML = $dataHead;

monthAndYear =
	document.getElementById("monthAndYear");
showCalendar(currentMonth, currentYear);

// Function to navigate to the next month
function next() {
	currentYear = currentMonth === 11 ?
		currentYear + 1 : currentYear;
	currentMonth = (currentMonth + 1) % 12;
	showCalendar(currentMonth, currentYear);
}

// Function to navigate to the previous month
function previous() {
	currentYear = currentMonth === 0 ?
		currentYear - 1 : currentYear;
	currentMonth = currentMonth === 0 ?
		11 : currentMonth - 1;
	showCalendar(currentMonth, currentYear);
}

// Function to jump to a specific month and year
function jump() {
	currentYear = parseInt(selectYear.value);
	currentMonth = parseInt(selectMonth.value);
	showCalendar(currentMonth, currentYear);
}

// Function to display the calendar
function showCalendar(month, year) {
	let firstDay = new Date(year, month, 1).getDay();
	tbl = document.getElementById("calendar-body");
	tbl.innerHTML = "";
	monthAndYear.innerHTML = months[month] + " " + year;
	selectYear.value = year;
	selectMonth.value = month;

	let date = 1;
	for (let i = 0; i < 6; i++) {
		let row = document.createElement("tr");
		for (let j = 0; j < 7; j++) {
			if (i === 0 && j < firstDay) {
				cell = document.createElement("td");
				cellText = document.createTextNode("");
				cell.appendChild(cellText);
				row.appendChild(cell);
			} else if (date > daysInMonth(month, year)) {
				break;
			} else {
				cell = document.createElement("td");
				cell.setAttribute("data-date", date);
				cell.setAttribute("data-month", month + 1);
				cell.setAttribute("data-year", year);
				cell.setAttribute("data-month_name", months[month]);
				cell.className = "date-picker";
				cell.innerHTML = "<span>" + date + "</span>";

				if (
					date === today.getDate() &&
					year === today.getFullYear() &&
					month === today.getMonth()
				) {
					cell.className = "date-picker selected";
				}

				// Check if there are events on this date
				if (hasEventOnDate(date, month, year)) {
					cell.classList.add("event-marker");
					cell.appendChild(
						createEventTooltip(date, month, year)
				);
				}

				row.appendChild(cell);
				date++;
			}
		}
		tbl.appendChild(row);
	}

	displayCalendars();
}

// Function to create an event tooltip
function createEventTooltip(date, month, year) {
	let tooltip = document.createElement("div");
	tooltip.className = "event-tooltip";
	let eventsOnDate = getEventsOnDate(date, month, year);
	for (let i = 0; i < eventsOnDate.length; i++) {
		let event = eventsOnDate[i];
		let eventDate = new Date(event.date);
		let eventText = `<strong>${event.title}</strong> - 
			${event.description} on 
			${eventDate.toLocaleDateString()}`;
		let eventElement = document.createElement("p");
		eventElement.innerHTML = eventText;
		tooltip.appendChild(eventElement);
	}
	return tooltip;
}

// Function to get events on a specific date
function getEventsOnDate(date, month, year) {
    result = [];
    for (let i = 0; i < events.length; i++) {
        let event = events[i];
        let eventDate = new Date(event.date);
        if (
            eventDate.getDate() === date &&
            eventDate.getMonth() === month &&
            eventDate.getFullYear() === year
        ) {
            for (let j = 0; j < user_calendars.length; j++) {
                let calendar = user_calendars[j];
                if (calendar.id == event.calendar_id) {
                    result.push(event);
                }
            }
        }
    }
    return result;
}

// Function to check if there are events on a specific date
function hasEventOnDate(date, month, year) {
	return getEventsOnDate(date, month, year).length > 0;
}

// Function to get the number of days in a month
function daysInMonth(iMonth, iYear) {
	return 32 - new Date(iYear, iMonth, 32).getDate();
}

// Call the showCalendar function initially to display the calendar
showCalendar(currentMonth, currentYear);