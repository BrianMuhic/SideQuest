// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// Auth
// -------------------------------------------------------------------------------------------------------------------

let authActiveTab = 'login';

function getCsrfToken() {
	const tokenMeta = document.querySelector('meta[name="csrf-token"]');
	return tokenMeta ? tokenMeta.getAttribute('content') : '';
}

function addCsrfToken(formData) {
	const csrfToken = getCsrfToken();
	if (csrfToken && !formData.has('csrf_token')) {
		formData.append('csrf_token', csrfToken);
	}
}

function authErrorMessage(xhr, fallbackMessage) {
	const payload = (xhr && xhr.responseJSON) || {};

	if (payload.error && typeof payload.error === 'string') {
		return payload.error;
	}

	const firstValue = Object.values(payload)[0];
	if (Array.isArray(firstValue) && firstValue.length) {
		return String(firstValue[0]);
	}
	if (typeof firstValue === 'string') {
		return firstValue;
	}

	return fallbackMessage;
}

function authToggle() {
	const widget = document.getElementById('panel-auth');
	const dropdown = document.getElementById('auth-dropdown');
	dropdown.hidden = !dropdown.hidden;
	widget.classList.toggle('open', !dropdown.hidden);
}

function authClose() {
	const widget = document.getElementById('panel-auth');
	const dropdown = document.getElementById('auth-dropdown');
	if (dropdown) dropdown.hidden = true;
	if (widget) widget.classList.remove('open');
}

function authTab(tab) {
	if (!document.getElementById('panel-auth')) return;

	authActiveTab = tab;
	document.getElementById('tab-login').classList.toggle('active', tab === 'login');
	document.getElementById('tab-register').classList.toggle('active', tab === 'register');
	document.getElementById('login-form').style.display = tab === 'login' ? '' : 'none';
	document.getElementById('register-form').style.display = tab === 'register' ? '' : 'none';
	document.getElementById('auth-btn').textContent = tab === 'login' ? 'Sign in' : 'Sign up';
	document.getElementById('login-error').textContent = '';
	document.getElementById('register-error').textContent = '';
}

function authSubmit() {
	if (authActiveTab === 'login') authLogin();
	else authRegister();
}

function initAuth() {
	const widget = document.getElementById('panel-auth');
	if (!widget) return;

	const loginForm = document.getElementById('login-form');
	const registerForm = document.getElementById('register-form');

	loginForm.addEventListener('submit', function(e) {
		e.preventDefault();
		authLogin();
	});

	registerForm.addEventListener('submit', function(e) {
		e.preventDefault();
		authRegister();
	});

	// Close dropdown when clicking outside the widget
	document.addEventListener('click', function(e) {
		if (!widget.contains(e.target)) {
			authClose();
		}
	});

	authTab('login');
}

function authLogin() {
	const form = document.getElementById('login-form');
	const data = new FormData(form);
	addCsrfToken(data);

	$.ajax({
		type: 'POST',
		url: '/account/login',
		data: data,
		processData: false,
		contentType: false,
	}).done(function(res) {
		document.getElementById('login-error').textContent = '';
		document.getElementById('register-error').textContent = '';
		document.getElementById('user-name').textContent = res.username;
		document.body.classList.add('authenticated');
		form.reset();
		authClose();
	}).fail(function(xhr) {
		document.getElementById('login-error').textContent = authErrorMessage(xhr, 'Login failed');
	});
}

function authRegister() {
	const form = document.getElementById('register-form');
	const data = new FormData(form);
	addCsrfToken(data);

	$.ajax({
		type: 'POST',
		url: '/account/register',
		data: data,
		processData: false,
		contentType: false,
	}).done(function(res) {
		document.getElementById('login-error').textContent = '';
		document.getElementById('register-error').textContent = '';
		document.getElementById('user-name').textContent = res.username;
		document.body.classList.add('authenticated');
		form.reset();
		authTab('login');
		authClose();
	}).fail(function(xhr) {
		document.getElementById('register-error').textContent = authErrorMessage(xhr, 'Registration failed');
	});
}

function authLogout() {
	$.ajax({
		type: 'POST',
		url: '/account/logout',
	}).done(function() {
		document.getElementById('user-name').textContent = '';
		document.body.classList.remove('authenticated');
		document.getElementById('login-form').reset();
		document.getElementById('register-form').reset();
		authTab('login');
		authClose();
	}).fail(ajaxFailure);
}
