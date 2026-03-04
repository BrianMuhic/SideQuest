// jshint esversion: 6
'use strict';

// -------------------------------------------------------------------------------------------------------------------
// DataTable Creation and Configuration
// -------------------------------------------------------------------------------------------------------------------

const datatableCreate = ($table, headers, removeClass = true) => {
	if (removeClass) {
		$table.removeClass();
	}
	$table.addClass("ui-widget ui-widget-content");

	const $headerRow = $("<tr>").addClass("ui-widget-header");
	$.each(headers, (index, value) => {
		const $th = $("<th>");
		$th.text(value);
		$th.attr("scope", "col");
		$headerRow.append($th);
	});

	const $thead = $("<thead>").append($headerRow);
	const $tbody = $("<tbody>");

	$table.empty().append($thead).append($tbody);
};

const dataTableConfig = (dataUrl, dataArgs = null, searching = true, paging = true) => {
	const firstRow = searching ? `<'row button-row'<'datatable-custom-container'f'B>>` : ``;
	const lastRow = paging ? `<'row datatable-bottom-row' <'col-6'<'info-container'i><'length-menu-control'l>><'col-6'p>>` : "";

	return {
		ajax: {
			type: "POST",
			url: dataUrl,
			contentType: "application/json",
			data: dataArgs
		},
		rowId: (data) => `row-${data.id}`,
		searching: searching,
		pageLength: 25,
		paging: paging,
		info: paging,
		autoWidth: false,
		scrollX: true,
		scrollY: '600px',
		order: [[1, "asc"]],
		select: { style: "single", selector: "td" },
		dom: `${firstRow}<'row'tr>${lastRow}`,
		serverSide: false,
		lengthMenu: [[10, 25, 50, 100, -1], ['10', '25', '50', '100', 'All']],
		buttons: [],
		language: {
			emptyTable: "No Records",
			info: "_TOTAL_ rows&nbsp;&nbsp;",
			infoFiltered: "",
			lengthMenu: "_MENU_ per page",
		},
		initComplete: () => {
			addCustomControls();
		},
		createdRow: (row) => $(row).find('td').addClass('truncate'),
	};
};

const addCustomControls = () => {
	$(".dt-buttons").prepend($('#custom-controls').detach());
};

const reloadTable = ($table, callback = null, resetPaging = false) => {
	$table.DataTable().ajax.reload(callback, resetPaging);
};

const deselectAllRows = ($table) => {
	$table.DataTable().rows().deselect();
};

// -------------------------------------------------------------------------------------------------------------------
// DataTable Column Search
// -------------------------------------------------------------------------------------------------------------------

const _dataTableColumnSearch = (datatable, column, searchTerm, regexp = false) => {
	if (!regexp && searchTerm) {
		searchTerm = `^${searchTerm}$`; // Make search exact
	}
	datatable.columns([column]).search(searchTerm, true, regexp).draw();
};

const _fieldName = ($table, columnNum) => {
	return `${$table.attr("id")}_${columnNum}`;
};

const _datatableAddSearchField = ($table, column, field) => {
	const $th = $table.find('th').eq(column);
	const label = $th.text();
	$th.addClass("searchable");
	$th.html(`
		<div class="table-header-with-search">
			<div id="${field}-header">
				<span>${label}</span>
			</div>
			<input type="text" id="${field}-search" class="table-header-search" placeholder="Search..."/>
		</div>
	`);
};

const datatableAddSearchFields = ($table, columns) => {
	for (const column of columns) {
		_datatableAddSearchField($table, column, _fieldName($table, column));
	}
};

const _datatableClickSearch = (datatable, column, field) => {
	const $search = $(`#${field}-search`);
	$search.val("").toggle().focus();
	_dataTableColumnSearch(datatable, column, "");
};

const _datatableSetupSearchField = (datatable, column, field) => {
	const $outerDiv = $(`#${field}-header`).parent().parent();
	$outerDiv.on("click", () => {
		_datatableClickSearch(datatable, column, field);
		return false; // Prevent triggering ordering
	});
	$(`#${field}-search`).on("keyup", (e) => {
		_dataTableColumnSearch(datatable, column, e.target.value, true);
	});
};

const datatableSetupSearchFields = ($table, columns) => {
	const datatable = $table.DataTable();
	for (const column of columns) {
		_datatableSetupSearchField(datatable, column, _fieldName($table, column));
	}
};

// -------------------------------------------------------------------------------------------------------------------
// DataTable Select Fields
// -------------------------------------------------------------------------------------------------------------------

const buildSelect = (options, uniqueId, className = "", selectDefault = false, valueSelected = null, onchange = null) => {
	const onchangeTxt = onchange ? ` onchange="${onchange}"` : "";
	let html = `<select class="${className}" name="${uniqueId}" id="${uniqueId}" ${onchangeTxt}>`;

	if (selectDefault && valueSelected === null) {
		html += `<option disabled hidden selected>- select -</option>`;
	}

	for (const [value, name] of Object.entries(options)) {
		const isSelected = value == valueSelected;
		html += `<option value="${value}"${isSelected ? " selected" : ""}>${name}</option>`;
	}

	html += `</select>`;
	return html;
};

const _datatableAddSelectField = ($table, column, field, options) => {
	const $th = $table.find('th').eq(column);
	const label = $th.text();
	const selectId = `${field}-select`;
	const select = buildSelect(options, selectId, "table-header-search", true);

	$th.addClass("searchable");
	$th.html(`
		<div class="table-header-with-search">
			<div id="${field}-header">
				<span>${label}</span>
			</div>
			${select}
		</div>
	`);
};

const datatableAddSelectFields = ($table, columns, options) => {
	for (let i = 0; i < columns.length; i++) {
		_datatableAddSelectField($table, columns[i], _fieldName($table, columns[i]), options[i]);
	}
};

const _datatableSetupSelectField = (datatable, column, field) => {
	const $select = $(`#${field}-select`);
	const $outerDiv = $(`#${field}-header`).parent().parent();

	$select.on("change", function() {
		_dataTableColumnSearch(datatable, column, this.value);
		return false;
	});

	$select.on("click", () => false);

	$outerDiv.on("click", () => {
		$select.toggle();
		$select.val(null);
		_dataTableColumnSearch(datatable, column, "");
		return false;
	});
};

const datatableSetupSelectFields = ($table, columns) => {
	const datatable = $table.DataTable();
	for (const column of columns) {
		_datatableSetupSelectField(datatable, column, _fieldName($table, column));
	}
};

// -------------------------------------------------------------------------------------------------------------------
// DataTable Export
// -------------------------------------------------------------------------------------------------------------------

const exportNumColumns = ($table) => {
	const numCols = $table.find("tr:first th").length - 1;
	const columns = [];
	for (let i = 0; i < numCols; i++) {
		columns.push(i + 1);
	}
	return columns;
};

const elementsAtIndexes = (array, indexes) => {
	return indexes.map(index => array[index]);
};

const dataToExport = (url, body, columns) => {
	const jsonResult = $.ajax({
		async: false,
		type: "POST",
		url: url,
		contentType: "application/json",
		dataType: "json",
		data: JSON.stringify({}),
	});

	body.length = 0;
	const data = jsonResult.responseJSON.data;

	if (columns === null) {
		body.push(...data);
	} else {
		for (const row of data) {
			body.push(elementsAtIndexes(row, columns));
		}
	}
};

const exportButton = (title, tableId, dataUrl = "", formalBody = null, columns = null) => {
	const exportOptions = {
		format: {
			header: (data) => {
				const regex = /<span>(.*?)<\/span>/g;
				const matches = regex.exec(data);
				return matches ? matches[1] : data;
			}
		}
	};

	if (columns !== null) {
		exportOptions.columns = columns;
	}

	if (dataUrl === "") {
		// Client-side
		exportOptions.columns = exportNumColumns(tableId);
	} else {
		// Server-side
		exportOptions.customizeData = (d) => {
			dataToExport(dataUrl, d.body, columns);
		};
	}

	if (formalBody) {
		exportOptions.format.body = formalBody;
	}

	return {
		extend: 'excel',
		title: title,
		text: "Export <span class='loading-spinner' style='display: none;'> <i class='fa fa-spinner fa-spin'></i> </span>",
		className: "small-btn",
		footer: false,
		exportOptions: exportOptions,
		action: function(e, dt, node, config) {
			const action = this;
			$(".loading-spinner").show();
			setTimeout(() => {
				$.fn.DataTable.ext.buttons.excelHtml5.action.call(action, e, dt, node, config);
				$(".loading-spinner").hide();
			}, 1000);
		}
	};
};
