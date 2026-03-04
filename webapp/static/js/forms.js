// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// Form Validation and Error Display
// -------------------------------------------------------------------------------------------------------------------

const ERROR_COLOR = "#F00";
const ERROR_BG_COLOR = "#FAA";

const highlightFields = (formId, fields) => {
	fields.forEach((field) => {
		$(`#${formId} input[name=${field}]`).css("background-color", ERROR_BG_COLOR);
		$(`#${formId} label[for=${field}]`).css("color", ERROR_COLOR);
	});
};

const highlightReset = (formId) => {
	$(`#${formId} input`).css("background-color", "");
	$(`#${formId} label`).css("color", "");
};

const displayErrors = (formId, errors) => {
	errors.forEach((error) => {
		const location = error.loc[1];
		const msg = error.msg;

		highlightFields(formId, [location]);
		const $parentDiv = $(`#${formId}`).find(`#${location}`).closest(".control-holder");
		$parentDiv.prepend(`<div class='error-message'>${msg}</div>`);
	});
};

const displayError = (formId, inputId, errorMsg) => {
	highlightFields(formId, [inputId]);
	const $parentDiv = $(`#${formId}`).find(`#${inputId}`).closest(".control-holder");
	$parentDiv.prepend(`<div class='error-message'>${errorMsg}</div>`);
};

const clearErrors = (formId) => {
	highlightReset(formId);
	$(`#${formId} .error-message`).remove();
};

// -------------------------------------------------------------------------------------------------------------------
// Input Utilities
// -------------------------------------------------------------------------------------------------------------------

const keypressNumberOnly = (event) => {
	const regex = /^[0-9]+$/;
	const key = String.fromCharCode(event.charCode || event.which);
	if (!regex.test(key)) {
		event.preventDefault();
		return false;
	}
};

const submitOnce = (button) => {
	button.disabled = true;
	button.textContent = "Submitting...";
	button.form.submit();
};

const preventDoubleSubmission = () => {
	$('form').submit(function() {
		$(this).find(':submit').attr('disabled', 'disabled');
	});
};

// Prevent double submission on page load
$(() => {
	preventDoubleSubmission();
});
