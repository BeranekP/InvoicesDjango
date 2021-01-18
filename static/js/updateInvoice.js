itemsToggle = document.getElementById('items');
itemsToggle.addEventListener('change', myfun);

function myfun(e) {
  b = 1;
  rowidx = 0;
  if (document.getElementById('btnAddRow') != null) {
    b = 0;
    rows = document.getElementsByClassName('invoiceItems');
    rowidx = rows.length - 1 + 1;
  }
  if (itemsToggle.checked) {
    var r = document.getElementById('itemList');
    var row = document.createElement('div');
    row.classList.add('w-100', 'row', 'mt-2', 'invoiceItems');
    var col1 = document.createElement('div');
    col1.classList.add('col-3');
    var col2 = document.createElement('div');
    col2.classList.add('col-3');
    var col3 = document.createElement('div');
    col3.classList.add('col-3');
    var col4 = document.createElement('div');
    col4.classList.add('col-3');

    r.appendChild(row);
    row.appendChild(col1);
    row.appendChild(col2);
    row.appendChild(col3);
    row.appendChild(col4);

    var name = document.createElement('input');
    name.classList.add('form-control');
    name.setAttribute('type', 'text');
    name.setAttribute('name', 'items' + rowidx.toString() + '[]');
    name.setAttribute('placeholder', 'název');
    name.id = 'name' + rowidx.toString();
    var pcs = document.createElement('input');
    pcs.setAttribute('type', 'number');
    pcs.setAttribute('name', 'items' + rowidx.toString() + '[]');
    pcs.setAttribute('placeholder', 'ks');
    pcs.setAttribute('oninput', 'itemUpdate()');
    pcs.classList.add('form-control');
    pcs.id = 'pcs' + rowidx.toString();
    var price_pcs = document.createElement('input');
    price_pcs.setAttribute('type', 'number');
    price_pcs.setAttribute('name', 'items' + rowidx.toString() + '[]');
    price_pcs.setAttribute('placeholder', 'Kč/ks');
    price_pcs.setAttribute('step', '0.01');
    price_pcs.setAttribute('oninput', 'itemUpdate()');
    price_pcs.classList.add('form-control');
    price_pcs.id = 'price_pcs' + rowidx.toString();
    var total = document.createElement('input');
    total.setAttribute('type', 'number');
    total.setAttribute('name', 'items' + rowidx.toString() + '[]');
    total.setAttribute('placeholder', 'celkem');
    total.setAttribute('step', '0.01');
    total.classList.add('form-control');
    total.id = 'total' + rowidx.toString();

    col1.appendChild(name);
    col2.appendChild(pcs);
    col3.appendChild(price_pcs);
    col4.appendChild(total);

    document
      .getElementById('pcs' + rowidx.toString())
      .addEventListener('input', function () {
        var ppcs = document.getElementById('price_pcs' + rowidx.toString())
          .value;

        document.getElementById('total' + rowidx.toString()).value =
          this.value * ppcs;
      });

    document
      .getElementById('price_pcs' + rowidx.toString())
      .addEventListener('input', function () {
        var ppcs = document.getElementById('pcs' + rowidx.toString()).value;

        document.getElementById('total' + rowidx.toString()).value =
          this.value * ppcs;
      });

    if (b == 1) {
      btnroot = document.getElementById('addRow');
      var btn = document.createElement('input');
      btn.id = 'btnAddRow';
      btn.setAttribute('type', 'button');
      btn.setAttribute('value', '+');
      btn.setAttribute('title', 'Přidat řádek');
      btn.setAttribute('onclick', 'myfun()');
      btn.classList.add('btn', 'btn-success');
      btnroot.appendChild(btn);
    }
  } else {
    var r = document.getElementById('itemList');
    r.innerHTML = '';
    btnroot = document.getElementById('addRow');
    btnroot.innerHTML = '';
  }
}

function getItems() {
  var check = '{{ invoice.has_items }}';

  if (check == 'True') {
    console.log(check);
    var i = 0;
    var e = new Event('change');
    ('{% for item in items  %}');
    itemsToggle.dispatchEvent(e);
    itemName = document.getElementById('name' + i.toString());
    pcs = document.getElementById('pcs' + i.toString());
    price_pcs = document.getElementById('price_pcs' + i.toString());
    total = document.getElementById('total' + i.toString());

    itemName.setAttribute('value', '{{ item.item_name }}');
    pcs.setAttribute('value', '{{ item.num_items }}');
    price_pcs.setAttribute('value', "{{ item.price_item|stringformat:'d'}}");
    total.setAttribute('value', "{{ item.price|stringformat:'d'}}");
    i = i + 1;
    ('{% endfor %}');
  }
}
getItems();

function itemUpdate(e) {
  itemlist = document.getElementById('itemList').getElementsByClassName('row');
  price = document.getElementById('amountInput');
  s = [];
  Array.from(itemlist).forEach(function (e) {
    ch = e.getElementsByTagName('input');
    ch[3].value = ch[1].value * ch[2].value;
    s.push(Number(ch[3].value));
  });
  const reducer = (accumulator, currentValue) => accumulator + currentValue;
  price.value = s.reduce(reducer);
}
