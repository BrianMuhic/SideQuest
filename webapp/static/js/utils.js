// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// AJAX Utilities
// -------------------------------------------------------------------------------------------------------------------

const postJson = (url, json) => {
	return $.ajax({
		type: "POST",
		url: url,
		contentType: "application/json",
		data: JSON.stringify(json)
	});
};

const ajaxFailure = (data, status, error) => {
	console.error('Ajax Error:', error, data.responseText);
	alert(`Error: ${error}\n${data.responseText}`);
};

// -------------------------------------------------------------------------------------------------------------------
// Show/Hide Utilities
// -------------------------------------------------------------------------------------------------------------------

const show = ($element, showing) => {
	if (showing) {
		$element.show();
	} else {
		$element.hide();
	}
};

const showIf = ($element, $checkbox) => {
	$checkbox.on("change", () => {
		show($element, $checkbox.prop("checked"));
	});
	$checkbox.trigger("change");
};

const showIfNot = ($element, $checkbox) => {
	$checkbox.on("change", () => {
		show($element, !$checkbox.prop("checked"));
	});
	$checkbox.trigger("change");
};

// -------------------------------------------------------------------------------------------------------------------
// Password Visibility Toggle
// -------------------------------------------------------------------------------------------------------------------

const togglePasswordVisibility = (inputId) => {
	const input = document.getElementById(inputId);
	if (input.type === "password") {
		input.type = "text";
	} else {
		input.type = "password";
	}
};

// -------------------------------------------------------------------------------------------------------------------
// Tab Navigation
// -------------------------------------------------------------------------------------------------------------------

const activateTab = (tabId) => {
	$(".active").removeClass("active").removeAttr("aria-current");
	if (tabId) {
		$(`#${tabId}`).addClass("active").attr("aria-current", "page");
	}
};
