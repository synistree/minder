function formatObjectAsJSON(obj, excludeInternal = true, indent = 4) {
    return JSON.stringify(obj, function(key, value) {
        if (excludeInternal && key.startsWith("_"))
            return undefined;

        return value;
    }, indent);
}

String.prototype.toTitleCase = function () {
  return this.replace(/\w\S*/g, function (txt) {
    return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
  });
};

function editEntry() {
  var row = $('table tbody tr.selected');
  var id = row.data('id');
  var entityName = row.data('entity_name');

  console.log(`Handling edit of "${entityName.toTitleCase()}" for ID ${id}`);

  if (onEditHandler != null) {
    onEditHandler(id);
  }

  $('#detail-modal').modal('toggle');

  localStorage.setItem('lastPage', window.location.href);
  window.location.href = `/edit/${entityName}/${id}`;
}

function setupTable(entityName, targetAttr, columns = [], paginate = false, responsive = true, select = 'single', onEditHandler = null) {
  var entityName = entityName.toLowerCase();
  var tableName = `#${entityName}_table`;

  var tbl = $(tableName).DataTable({
    buttons: true,
    responsive: responsive,
    select: select,
    paginate: paginate,
    columnDefs: columns,
    hover: true,
    ajax: {
      url: `/api/${entityName}s`,
      dataSrc: ''
    },
    dom: 'Bfrtip',
    buttons: [{
      text: 'Edit Entry',
      action: function (e, dt, node, config) {
        var curEntry = $('tbody tr.selected');
        if(!curEntry) {
          console.log("No selected entry to edit.");
          return false;
        }

        editEntry();
      }
    }]
  });

  $('#detail-modal .edit-button').on('click', function() {
    editEntry();
  });

  $(`${tableName}`).on('click', 'tbody tr', function (e) {
    if (!e.metaKey) {
      console.log(`No meta key pressed while clicking on row. Ignoring.`);
      return;
    }

    row = $(this);

    if (!row.hasClass('selected')) {
      return;
    }

    console.log(`Row ${row} is selected.`);
    var data = tbl.row(this).data();
    var dataJSON = formatObjectAsJSON(data);
    var targetValue = data[targetAttr];

    console.log(`Pulling ${entityName} data for "${targetAttr}":\n${dataJSON}`);

    var editDetails = `${entityName.toTitleCase()} data for "<strong>${targetValue}</strong>"`;
    editDetails += `<br/><pre><code>${dataJSON}</code></pre>`
    $('#detail-modal-name').text(data.username);
    $('#detail-modal-type').text(entityName);
    $('#detail-modal-content').html(editDetails);
    $('#detail-modal .edit-button').data('id', data.id);
    $('#detail-modal .edit-button').data('entity_name', entityName);
    $('#detail-modal').modal('show');

    return false;
  });
}

// vim: set ts=2 sw=2 smarttab autoindent expandtab ft=javascript:
