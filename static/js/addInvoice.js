// items checkbox handler
itemsToggle = document.getElementById('items');
itemsToggle.addEventListener('change', myfun);

rowidx = 0; // row index number
// add "table" of invoice items
function myfun(e) {
  b = 1;

  if (document.getElementById('btnAddRow') != null) {
    b = 0; // prevent duplicating buttons
  }
  if (itemsToggle.checked) {
    var r = document.getElementById('itemList');
    var row = document.createElement('div');
    row.classList.add(
      'w-100',
      'mt-1',
      'mx-0',
      'row',
      'd-flex',
      'justify-content-around'
    );
    var col1 = document.createElement('div');
    col1.classList.add('col-3', 'px-1');
    var col2 = document.createElement('div');
    col2.classList.add('col-3', 'px-1');
    var col3 = document.createElement('div');
    col3.classList.add('col-3', 'px-1');
    var col4 = document.createElement('div');
    col4.classList.add('col-3', 'px-1');

    r.appendChild(row);
    row.appendChild(col1);
    row.appendChild(col2);
    row.appendChild(col3);
    row.appendChild(col4);

    // item name
    var name = document.createElement('input');
    name.classList.add('form-control');
    name.setAttribute('type', 'text');
    name.setAttribute('name', 'items' + rowidx.toString() + '[]');
    name.setAttribute('placeholder', 'název');
    name.id = 'name' + rowidx.toString();

    // no of pieces
    var pcs = document.createElement('input');
    pcs.setAttribute('type', 'number');
    pcs.setAttribute('name', 'items' + rowidx.toString() + '[]');
    pcs.setAttribute('placeholder', 'ks');
    pcs.setAttribute('oninput', 'itemUpdate()');
    pcs.classList.add('form-control');
    pcs.id = 'pcs' + rowidx.toString();

    // price per piece
    var price_pcs = document.createElement('input');
    price_pcs.setAttribute('type', 'number');
    price_pcs.setAttribute('name', 'items' + rowidx.toString() + '[]');
    price_pcs.setAttribute('placeholder', 'cena/ks');
    price_pcs.classList.add('form-control');
    price_pcs.setAttribute('oninput', 'itemUpdate()');
    price_pcs.id = 'price_pcs' + rowidx.toString();

    // total per item
    var total = document.createElement('input');
    total.setAttribute('type', 'number');
    total.setAttribute('name', 'items' + rowidx.toString() + '[]');
    total.setAttribute('placeholder', 'celkem');
    total.classList.add('form-control', 'totalPrice');
    total.id = 'total' + rowidx.toString();

    col1.appendChild(name);
    col2.appendChild(pcs);
    col3.appendChild(price_pcs);
    col4.appendChild(total);

    if (b == 1) {
      // add button for more rows if not created (first run)
      btnroot = document.getElementById('addRow');
      var btn = document.createElement('input');
      btn.id = 'btnAddRow';
      btn.setAttribute('type', 'button');
      btn.setAttribute('value', '+');
      btn.setAttribute('title', 'Přidat řádek');
      btn.setAttribute('onclick', 'myfun()');
      btn.classList.add('btn', 'btn-outline-success');
      btnroot.appendChild(btn);
    }
  } else {
    //delete items when unchecking check box
    var r = document.getElementById('itemList');
    r.innerHTML = '';
    btnroot = document.getElementById('addRow');
    btnroot.innerHTML = '';
  }
  rowidx++;
}

// Add aritmetic functionality, auto counting totals
function itemUpdate(e) {
  itemlist = document.getElementById('itemList').getElementsByClassName('row');
  price = document.getElementById('amountInput'); // total invoice price
  s = []; // totals per item
  Array.from(itemlist).forEach(function (item) {
    inputs = item.getElementsByTagName('input'); // 0 - name, 1 - pcs, 2 - price_pcs, 3 - total
    inputs[3].value = inputs[1].value * inputs[2].value;
    s.push(Number(inputs[3].value));
  });
  const sum = (accumulator, currentValue) => accumulator + currentValue;
  price.value = s.reduce(sum);
}


