  let currentSku = null;

  // ── SKU 6 (Product Lifestyle Mockup): category → scene suggestions ──
  // Previously referenced by the form's onchange but never defined, so picking
  // a category did nothing and `scene_setting` was always submitted empty.
  // Defining it here makes the picker work and gives every order a good scene.
  const PM_SCENES = {
    'Skincare / Beauty':        ['Bright bathroom shelf', 'Spa stones + towel', 'Morning windowsill', 'Pastel flat-lay', 'Marble vanity'],
    'Food & Beverage':          ['Rustic wood board', 'Dining table setting', 'Marble kitchen counter', 'Outdoor picnic', 'Café tabletop'],
    'Home Fragrance / Candles': ['Cozy living room', 'Bedside table', 'Bathtub ledge', 'Styled shelf vignette', 'Warm evening glow'],
    'Supplements / Wellness':   ['Kitchen counter', 'Gym floor', 'Bright breakfast table', 'Yoga mat + plants', 'Minimal studio'],
    'Electronics / Gadgets':    ['Modern desk setup', 'Minimal studio', 'In-hand lifestyle', 'Café workspace', 'Tech flat-lay'],
    'Apparel / Accessories':    ['Urban street', 'Studio seamless', 'Lifestyle bedroom', 'Outdoor nature', 'Flat-lay with props'],
    'Baby / Kids':              ['Soft nursery', 'Playmat scene', 'Bright bedroom', 'Cozy crib-side', 'Pastel flat-lay'],
    'Kitchen / Cookware':       ['On the stovetop', 'Styled kitchen counter', 'Dining table', 'Rustic wood board', 'Minimal studio'],
    'Stationery / Office':      ['Tidy desk setup', 'Flat-lay with props', 'Café workspace', 'Minimal studio', 'In-hand lifestyle'],
    'Lighting / Lamps':         ['Cozy living room', 'Bedside table', 'Reading nook', 'Modern desk', 'Evening ambience'],
    'Furniture / Home Décor':   ['Styled living room', 'Shelf vignette', 'Bedroom setting', 'Dining setup', 'Neutral studio'],
    'Other':                    ['Lifestyle in-use', 'Minimal studio', 'Natural daylight', 'Styled tabletop', 'Outdoor scene'],
  };

  function _pmSelectScene(chipEl, val) {
    var wrap = document.getElementById('pm-scene-chips');
    if (wrap) wrap.querySelectorAll('.pm-scene-chip').forEach(function (c) {
      c.style.background = '#fff'; c.style.border = '1px solid #D7DEE6'; c.style.color = '#374151';
    });
    if (chipEl) { chipEl.style.background = '#fffbe9'; chipEl.style.border = '1.5px solid var(--gold)'; }
    var box = document.getElementById('pm-scene-text');
    if (box) box.value = val;   // chips just pre-fill the always-typeable box
  }

  function updatePMScenes(cat) {
    var wrap = document.getElementById('pm-scene-chips');
    if (!wrap) return;
    var scenes = PM_SCENES[cat] || PM_SCENES['Other'];
    wrap.innerHTML = '';
    scenes.forEach(function (s, i) {
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'pm-scene-chip';
      chip.textContent = s;
      chip.style.cssText = 'border:1px solid #D7DEE6;background:#fff;color:#374151;border-radius:16px;padding:5px 12px;font-size:0.82rem;cursor:pointer;margin:0 6px 6px 0;';
      chip.onclick = function () { _pmSelectScene(chip, s); };
      wrap.appendChild(chip);
      if (i === 0) _pmSelectScene(chip, s); // sensible default; client can edit or retype
    });
  }

  // ── SKU 7 (Instagram Carousel): format selector → adaptive inputs + price ──
  function updateCarouselFormat(fmt) {
    var byId = function (id) { return document.getElementById(id); };
    var show = function (id, on) { var e = byId(id); if (e) e.style.display = on ? '' : 'none'; };
    var isText = fmt === 'Text-led', isImage = fmt === 'Image + Text',
        isPhoto = fmt === 'Photo-only', isInfo = fmt === 'Infographic';

    show('ic-keypoints', isText || isImage);
    show('ic-infographic-data', isInfo);
    show('ic-visualstyle', isText || isImage);

    var kp = document.querySelector('#ic-keypoints input[name="key_points[]"]');
    if (kp) kp.required = (isText || isImage);
    var dataEl = byId('ic-infographic-data-input');
    if (dataEl) dataEl.required = isInfo;
    var img = byId('ic-images-input');
    if (img) img.required = isPhoto;

    var lbl = byId('ic-images-label'), hint = byId('ic-images-hint');
    if (lbl && hint) {
      if (isPhoto) { lbl.innerHTML = 'Your image set <span class="required">*</span>'; hint.textContent = 'These photos ARE the slides — add 5–10 strong, on-brand images.'; }
      else if (isImage) { lbl.textContent = 'Product / Reference Photos (optional)'; hint.textContent = 'Optional — the visuals behind your text. Add as many as you like, or let the pilot source them.'; }
      else { lbl.textContent = 'Product / Reference Photos (optional)'; hint.textContent = 'Optional — anything visual that guides the pilot.'; }
    }
    var tl = byId('ic-topic-label');
    if (tl) tl.innerHTML = (isPhoto ? 'Theme / vibe' : "Topic — what's it about?") + ' <span class="required">*</span>';

    var amt = byId('ic-price-amount'), brk = byId('ic-price-breakdown');
    if (amt) amt.textContent = isInfo ? '₹899' : '₹649';
    if (brk) brk.textContent = isInfo ? 'Flat rate · data-viz carousel · 2 options per slide'
                                      : 'Flat rate · 2 options per slide · ZIP (PNGs + caption.txt)';
    var ribbon = byId('submitPriceRibbon');
    if (ribbon) ribbon.textContent = isInfo ? '₹899' : '₹649';

    var help = byId('ic-format-help');
    if (help) {
      var msg = {
        'Text-led': 'Type-driven slides, minimal imagery. Best for tips, lists & frameworks.',
        'Image + Text': 'Photos with text overlays. Best for promos, product education & before/after.',
        'Photo-only': 'Pure imagery, little or no text. Best for lookbooks, showcases & visual dumps.',
        'Infographic': 'Charts, comparisons & step-by-step visuals. Data-heavy · ₹899 flat.'
      };
      help.textContent = msg[fmt] || '';
    }
  }


  function selectSku(sku, el) {
    document.querySelectorAll('.sku-pick').forEach(p => p.classList.remove('selected'));
    el.classList.add('selected');
    
    document.querySelectorAll('.sku-form').forEach(f => {
      f.classList.remove('visible');
      f.querySelectorAll('input, textarea, select').forEach(i => i.disabled = true);
    });
    
    const form = document.getElementById('form-' + sku);
    if (form) {
      form.classList.add('visible');
      form.querySelectorAll('input, textarea, select').forEach(i => i.disabled = false);
    }
    
    document.getElementById('taskTypeInput').value = sku;
    if (window.__VOICE_BRIEF_ENABLED__ !== false) {
      document.getElementById('voiceNoteSection').style.display = 'block';
    }
    document.getElementById('contactSection').style.display = 'block';
    document.getElementById('submitBar').style.display = 'flex';
    currentSku = sku;
    // BUG 9 fix: update price ribbon from the selected SKU card's price text
    const ribbon = document.getElementById('submitPriceRibbon');
    if (ribbon) {
      const spPrice = el.querySelector('.sp-price');
      // Use innerText to strip <small> tags (e.g. "flat", "/image")
      ribbon.textContent = spPrice ? spPrice.innerText.trim() : '';
    }
    // VS: override ribbon with live dynamic price (BUG 4/5 fix)
    if (sku === 'virtual_staging' && typeof updateVsPrice === 'function') updateVsPrice();
    // GROUP 2: delay scroll until form is visible so offsetTop is correct
    setTimeout(() => {
      const formEl = document.getElementById('form-' + sku);
      if (formEl) {
        window.scrollTo({top: formEl.offsetTop - 80, behavior: 'smooth'});
        try {
          parent.postMessage({__owScrollToOffset: formEl.offsetTop}, '*');
        } catch(e) {}
      }
    }, 50);
  }

  function changeQty(delta, sku, minVal) {
    const el = document.getElementById('qty-' + sku);
    const hid = document.getElementById('count-' + sku);
    if (!el) return;
    let v = parseInt(el.textContent) + delta;
    if (v < minVal) v = minVal;
    if (sku === 'bg_cleanup' && v > 10) v = 10;
    el.textContent = v;
    if (hid) hid.value = v;
    updatePrice(sku, v);
  }

  const UNIT_PRICES = {
    'bg_cleanup': 500, 'product_listing': 199, 'product_mockup': 299
  };

  function updatePrice(sku, count) {
    if (sku === 'bg_cleanup') {
      const amtEl = document.getElementById('pamt-bg_cleanup');
      const brkEl = document.getElementById('pbrk-bg_cleanup');
      if (amtEl) amtEl.textContent = '₹500';
      if (brkEl) brkEl.textContent = 'Flat rate · up to 10 images';
      return;
    }
    const unit = UNIT_PRICES[sku];
    if (!unit) return;
    const billableCount = count;
    const total = unit * billableCount;
    const amtEl = document.getElementById('pamt-' + sku);
    const brkEl = document.getElementById('pbrk-' + sku);
    const minEl = document.getElementById('pmin-' + sku);
    if (amtEl) amtEl.textContent = '₹' + total.toLocaleString('en-IN');
    if (brkEl) {
      const labels = {'product_listing':'product','product_mockup':'mockup'};
      brkEl.textContent = '₹' + unit + ' x ' + billableCount + ' ' + (labels[sku] || 'unit') + (billableCount>1?'s':'');
    }
    if (minEl) {
      minEl.style.display = 'none';
    }
  }

  // Virtual Staging — dynamic rooms
  let vsRoomCount = 1; // legacy — kept in case referenced elsewhere
  // Virtual Staging — dynamic labeled photo rows with POV A + POV B
  let vsPhotoCount = 1;
  const vsRoomOptions = ['Living Room','Living + Dining (Combined)','Dining Area','Kitchen','Master Bedroom','Master Bathroom','Bedroom 2','Bedroom 3','Bedroom 4','Bathroom','Balcony','Terrace','Study / Home Office','Lobby / Entrance','Exterior / Facade','Amenity (Pool / Gym)','Other'];
  function addVsPhotoRow() {
    if (vsPhotoCount >= 12) return;
    const idx = vsPhotoCount;
    vsPhotoCount++;
    const container = document.getElementById('vs-photo-rows');
    const row = document.createElement('div');
    row.className = 'vs-photo-row';
    row.style.cssText = 'display:grid;grid-template-columns:160px 1fr 1fr 1fr auto;gap:0.5rem;margin-bottom:0.6rem;align-items:start;';
    row.innerHTML = `
      <select name="room_labels[]" class="form-control" style="margin-top:0;">${vsRoomOptions.map(o=>`<option>${o}</option>`).join('')}</select>
      <div class="upload-box" style="margin:0;" id="box-vs-p${idx}a">
        <input type="file" name="room_photos[]" accept="image/*" onchange="showFile(this,'box-vs-p${idx}a')" required>
        <div class="upload-icon" style="font-size:0.9rem;margin:0;">📷</div>
        <div class="upload-label" style="font-size:0.75rem;">Upload</div>
        <div class="file-shown" style="font-size:0.68rem;"></div>
      </div>
      <div class="upload-box" style="margin:0;border-style:dashed;border-color:#f59e0b;background:#fffbeb;" id="box-vs-p${idx}b">
        <input type="file" name="room_photos_b[]" accept="image/*" onchange="showFile(this,'box-vs-p${idx}b')">
        <div class="upload-icon" style="font-size:0.9rem;margin:0;">📐</div>
        <div class="upload-label" style="font-size:0.75rem;color:#92400e;">Upload (optional)</div>
        <div class="file-shown" style="font-size:0.68rem;"></div>
      </div>
      <div class="upload-box" style="margin:0;border-style:dashed;border-color:#6366f1;background:#f5f3ff;" id="box-vs-mood${idx}">
        <input type="file" name="room_moodboards[]" accept="image/*,.pdf" onchange="showFile(this,'box-vs-mood${idx}')">
        <div class="upload-icon" style="font-size:0.9rem;margin:0;">🎨</div>
        <div class="upload-label" style="font-size:0.75rem;color:#4f46e5;">Upload Moodboard (optional)</div>
        <div class="file-shown" style="font-size:0.68rem;"></div>
      </div>
      <button type="button" onclick="this.closest('.vs-photo-row').remove()" style="margin-top:6px;background:none;border:none;color:#ef4444;cursor:pointer;font-size:1rem;line-height:1;" aria-label="Remove">✕</button>`;
    container.appendChild(row);
  }

  // ── Virtual Staging — tier selection + per-room surcharge (BUG 4/5 fix) ──
  var currentVsTier = 'full';
  var VS_TIER = {
    'starter': { base: 649, maxRooms: 2, extraPerRoom: 0 },
    'full':    { base: 799, maxRooms: 4, extraPerRoom: 100 }
  };

  function updateVsPrice() {
    var info = VS_TIER[currentVsTier] || VS_TIER['full'];
    var rooms = document.querySelectorAll('#vs-photo-rows .vs-photo-row').length;
    var extra = Math.max(0, rooms - info.maxRooms);
    var total = info.base + extra * info.extraPerRoom;
    var priceEl = document.getElementById('vs-price-display');
    var brkEl   = document.getElementById('vs-price-breakdown');
    var surchEl = document.getElementById('vs-surcharge-note');
    if (priceEl) priceEl.textContent = '₹' + total.toLocaleString('en-IN');
    if (brkEl) {
      brkEl.textContent = extra > 0
        ? '₹' + info.base + ' base + ' + extra + ' × ₹100 extra room' + (extra > 1 ? 's' : '')
        : (currentVsTier === 'starter' ? 'Flat rate · 2 rooms · one render per room' : 'Flat rate · up to 4 rooms staged · one render per room');
    }
    if (surchEl) {
      if (extra > 0) {
        surchEl.style.display = 'block';
        surchEl.textContent = '⚠ Surcharge: ' + extra + ' extra room' + (extra > 1 ? 's' : '') + ' × ₹100 = +₹' + (extra * 100);
      } else {
        surchEl.style.display = 'none';
      }
    }
    var ribbon = document.getElementById('submitPriceRibbon');
    if (ribbon && currentSku === 'virtual_staging') ribbon.textContent = '₹' + total.toLocaleString('en-IN');
  }

  document.querySelectorAll('input[name="vs_tier"]').forEach(function(r) {
    r.addEventListener('change', function() { currentVsTier = this.value; updateVsPrice(); });
  });

  // MutationObserver keeps surcharge live when rows are added or removed
  var vsRowContainer = document.getElementById('vs-photo-rows');
  if (vsRowContainer) {
    new MutationObserver(function() { updateVsPrice(); }).observe(vsRowContainer, { childList: true });
  }

  // Property Reel — dynamic labeled photo rows with POV A + POV B
  let prPhotoCount = 1;
  function addPrPhotoRow() {
    if (prPhotoCount >= 15) return;
    prPhotoCount++;
    const idx = prPhotoCount - 1;
    const container = document.getElementById('pr-photo-rows');
    const row = document.createElement('div');
    row.className = 'pr-photo-row';
    row.style.cssText = 'display:grid;grid-template-columns:160px 1fr 1fr 1fr auto;gap:0.5rem;margin-bottom:0.6rem;align-items:start;';
    const areaOptions = ['Exterior / Facade','Living Room','Living + Dining (Combined)','Dining Area','Kitchen','Master Bedroom','Master Bathroom','Bedroom 2','Bedroom 3','Bedroom 4','Bathroom','Balcony','Terrace','Study / Home Office','Lobby / Entrance','Amenity (Pool / Gym / Clubhouse)','Other'];
    row.innerHTML = `
      <select name="property_photos_label[]" class="form-control" style="margin-top:0;">${areaOptions.map(o=>`<option>${o}</option>`).join('')}</select>
      <div class="upload-box" style="margin:0;" id="box-pr-p${idx}a">
        <input type="file" name="property_photos" accept="image/*" onchange="showFile(this,'box-pr-p${idx}a')">
        <div class="upload-icon" style="font-size:0.9rem;margin:0;">📷</div>
        <div class="upload-label" style="font-size:0.75rem;">Upload</div>
        <div class="file-shown" style="font-size:0.68rem;"></div>
      </div>
      <div class="upload-box" style="margin:0;border-style:dashed;border-color:#f59e0b;background:#fffbeb;" id="box-pr-p${idx}b">
        <input type="file" name="property_photos_b" accept="image/*" onchange="showFile(this,'box-pr-p${idx}b')">
        <div class="upload-icon" style="font-size:0.9rem;margin:0;">📐</div>
        <div class="upload-label" style="font-size:0.75rem;color:#92400e;">Upload (optional)</div>
        <div class="file-shown" style="font-size:0.68rem;"></div>
      </div>
      <div class="upload-box" style="margin:0;border-style:dashed;border-color:#6366f1;background:#f5f3ff;" id="box-pr-mood${idx}">
        <input type="file" name="property_moodboards" accept="image/*,.pdf" onchange="showFile(this,'box-pr-mood${idx}')">
        <div class="upload-icon" style="font-size:0.9rem;margin:0;">🎨</div>
        <div class="upload-label" style="font-size:0.75rem;color:#4f46e5;">Upload Moodboard (optional)</div>
        <div class="file-shown" style="font-size:0.68rem;"></div>
      </div>
      <button type="button" onclick="this.closest('.pr-photo-row').remove()" style="margin-top:6px;background:none;border:none;color:#ef4444;cursor:pointer;font-size:1rem;line-height:1;" aria-label="Remove">✕</button>`;
    container.appendChild(row);
  }

  function showFile(input, boxId) {
    const box = document.getElementById(boxId);
    if (!box) return;
    if (input.files && input.files[0]) {
      box.classList.add('has-file');
      // Some upload boxes don't include a .file-shown element in markup —
      // create one on the fly so EVERY box confirms the uploaded file.
      let nameEl = box.querySelector('.file-shown');
      if (!nameEl) {
        nameEl = document.createElement('div');
        nameEl.className = 'file-shown';
        box.appendChild(nameEl);
      }
      const n = input.files.length;
      nameEl.textContent = n > 1
        ? ('✓ ' + n + ' files selected')
        : ('✓ ' + input.files[0].name);
    } else {
      box.classList.remove('has-file');
      const nameEl = box.querySelector('.file-shown');
      if (nameEl) nameEl.textContent = '';
    }
  }

  function showMultiFile(input, boxId, listId) {
    const box = document.getElementById(boxId);
    const listEl = document.getElementById(listId);
    if (!input.files || input.files.length === 0) return;
    box.classList.add('has-file');
    if (listEl) {
      listEl.innerHTML = '';
      Array.from(input.files).forEach((f, i) => {
        const chip = document.createElement('span');
        chip.className = 'file-chip-item';
        const shortName = f.name.length > 22 ? f.name.substring(0,20)+'…' : f.name;
        chip.innerHTML = `<span class="fc-name">📎 ${shortName}</span><button class="file-chip-remove" type="button" title="Remove" onclick="removeFileChip(this,'${boxId}','${listId}',${i})" aria-label="Remove">✕</button>`;
        listEl.appendChild(chip);
      });
    }
  }

  function removeFileChip(btn, boxId, listId, idx) {
    // Remove chip visually (can't truly remove from FileList - just grey it out)
    const chip = btn.closest('.file-chip-item');
    if (chip) { chip.style.opacity = '0.4'; chip.style.textDecoration = 'line-through'; btn.disabled = true; }
  }

  function showToast(msg, type) {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = 'toast toast-' + (type||'info');
    t.textContent = msg;
    c.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 400); }, 4000);
  }

  // Voice Brief recorder
  var _vnMediaRecorder = null;
  var _vnChunks = [];
  var _vnBlob = null;
  var _vnTimerInterval = null;
  var _vnSeconds = 0;

  function vnShow(state) {
    ['idle','recording','done','denied'].forEach(function(s){
      var el = document.getElementById('vn-' + s);
      if (el) el.style.display = (s === state) ? '' : 'none';
    });
  }

  function vnStart() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      vnShow('denied'); return;
    }
    navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream) {
      _vnChunks = [];
      _vnBlob = null;
      _vnSeconds = 0;
      document.getElementById('vn-timer').textContent = '0:00';

      var mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : (MediaRecorder.isTypeSupported('audio/ogg') ? 'audio/ogg' : '');
      var opts = mimeType ? {mimeType: mimeType} : {};
      _vnMediaRecorder = new MediaRecorder(stream, opts);

      _vnMediaRecorder.ondataavailable = function(e) {
        if (e.data && e.data.size > 0) _vnChunks.push(e.data);
      };
      _vnMediaRecorder.onstop = function() {
        stream.getTracks().forEach(function(t){ t.stop(); });
        _vnBlob = new Blob(_vnChunks, {type: mimeType || 'audio/webm'});
        var url = URL.createObjectURL(_vnBlob);
        document.getElementById('vn-playback').src = url;
        var mins = Math.floor(_vnSeconds / 60);
        var secs = _vnSeconds % 60;
        document.getElementById('vn-done-label').textContent =
          'Voice brief recorded (' + mins + ':' + (secs < 10 ? '0' : '') + secs + ')';
        clearInterval(_vnTimerInterval);
        vnShow('done');
        _vnMediaRecorder = null;
      };

      _vnMediaRecorder.start(200);
      vnShow('recording');

      _vnTimerInterval = setInterval(function() {
        _vnSeconds++;
        var m = Math.floor(_vnSeconds / 60);
        var s = _vnSeconds % 60;
        document.getElementById('vn-timer').textContent = m + ':' + (s < 10 ? '0' : '') + s;
      }, 1000);

    }).catch(function() {
      vnShow('denied');
    });
  }

  function vnStop() {
    if (_vnMediaRecorder && _vnMediaRecorder.state !== 'inactive') {
      _vnMediaRecorder.stop();
    }
    clearInterval(_vnTimerInterval);
  }

  function vnReset() {
    _vnBlob = null;
    _vnChunks = [];
    _vnSeconds = 0;
    clearInterval(_vnTimerInterval);
    if (_vnMediaRecorder && _vnMediaRecorder.state !== 'inactive') {
      _vnMediaRecorder.stop();
    }
    document.getElementById('vn-playback').src = '';
    vnShow('idle');
  }

  function vnFileChosen(input) {
    if (!input.files || !input.files[0]) return;
    _vnBlob = input.files[0];
    var url = URL.createObjectURL(_vnBlob);
    document.getElementById('vn-playback').src = url;
    document.getElementById('vn-done-label').textContent = 'Voice brief: ' + input.files[0].name;
    vnShow('done');
  }

  function activateFreePass() {
    document.getElementById('useFreePassInput').value = '1';
    var btn = document.getElementById('submitBtn');
    var fpBtn = document.getElementById('freePassBtn');
    if (fpBtn) { fpBtn.style.display = 'none'; }
    btn.textContent = '🎟 Submitting with Free Pass…';
    btn.style.background = '#f59e0b';
    btn.style.color = '#000';
    document.getElementById('orderForm').dispatchEvent(new Event('submit'));
  }

  function clearBgPhotoError() {
    const errEl = document.getElementById('bg-photo-error');
    if (errEl) errEl.style.display = 'none';
    const box = document.getElementById('box-bg-photos');
    if (box) box.style.borderColor = '';
  }

  // ── SKU 4 Background Cleanup — marketplace smart-branch lock ──
  // Amazon/Flipkart forces white bg + no shadow + JPG. We force-check those and
  // visually lock the groups (pointer-events) so the checked values still submit.
  // The server (orders.py) re-enforces the same rule, so this is UX, not trust.
  function applyBgLock() {
    var sel = document.querySelector('input[name="final_use"]:checked');
    var market = !!sel && sel.value === 'Amazon / Flipkart';
    var groups = ['bg-bgchips', 'bg-shadowchips', 'bg-fmtchips'];
    if (market) {
      var w = document.getElementById('bg-b1'); if (w) w.checked = true;   // Pure White
      var n = document.getElementById('bg-s1'); if (n) n.checked = true;   // No shadow
      var j = document.getElementById('bg-f2'); if (j) j.checked = true;   // JPG
      groups.forEach(function (id) { var g = document.getElementById(id); if (g) { g.style.pointerEvents = 'none'; g.style.opacity = '0.55'; } });
      var note = document.getElementById('bg-lock-note'); if (note) note.style.display = 'block';
    } else {
      groups.forEach(function (id) { var g = document.getElementById(id); if (g) { g.style.pointerEvents = ''; g.style.opacity = ''; } });
      var note2 = document.getElementById('bg-lock-note'); if (note2) note2.style.display = 'none';
    }
    onBgBackgroundChange();
  }

  function onBgBackgroundChange() {
    var sel = document.querySelector('input[name="final_use"]:checked');
    var market = !!sel && sel.value === 'Amazon / Flipkart';
    var bg = document.querySelector('input[name="background_type"]:checked');
    var wrap = document.getElementById('bg-custom-wrap');
    if (wrap) wrap.style.display = (!market && bg && bg.value === 'custom') ? 'block' : 'none';
  }

  async function submitOrder(e) {
    e.preventDefault();
    const btn = document.getElementById('submitBtn');
    const task = document.getElementById('taskTypeInput').value;
    if (!task) { showToast('Please select a task first.', 'error'); return; }

    // 1A: validate bg_cleanup requires at least one product photo
    if (task === 'bg_cleanup') {
      const photoInput = document.getElementById('bg-photos-input');
      if (!photoInput || photoInput.files.length === 0) {
        const errEl = document.getElementById('bg-photo-error');
        const box = document.getElementById('box-bg-photos');
        if (errEl) errEl.style.display = 'block';
        if (box) { box.style.borderColor = '#e53e3e'; box.scrollIntoView({behavior:'smooth', block:'center'}); }
        showToast('Please upload at least one product photo.', 'error');
        return;
      }
    }

    btn.disabled = true; btn.textContent = 'Submitting…';
    const fd = new FormData(document.getElementById('orderForm'));
    fd.append('csrf_token', document.querySelector('meta[name="csrf-token"]').content);
    if (_vnBlob) {
      var ext = (_vnBlob.type && _vnBlob.type.indexOf('ogg') !== -1) ? 'ogg' : 'webm';
      var fname = _vnBlob.name || ('voice_brief.' + ext);
      fd.append('voice_note', _vnBlob, fname);
    }
    try {
      const res = await fetch(window.__API_BASE__+'/submit-order', {method:'POST', body:fd, credentials:'include'});
      const data = await res.json();
      if (data.success) {
        if (data.requires_upfront_payment && data.payment_url) {
          btn.textContent = 'Redirecting to payment…';
          showToast(data.message || 'Redirecting to payment…', 'success');
          setTimeout(() => window.top.location.href = data.payment_url, 900);
        } else if (data.free_pass_used) {
          showToast('🎟 Free Pass used! Order confirmed.', 'success');
          setTimeout(() => window.top.location.href = '/client/orders', 1500);
        } else {
          showToast(data.message || 'Order placed!', 'success');
          setTimeout(() => window.top.location.href = '/client/orders', 2000);
        }
      } else {
        showToast(data.error || 'Something went wrong.', 'error');
        btn.disabled = false; btn.textContent = 'Submit Order';
      }
    } catch(err) {
      showToast('Network error. Please try again.', 'error');
      btn.disabled = false; btn.textContent = 'Submit Order';
    }
  }

  // Auto-select from URL param
  // Fetch user order count to show correct payment note
  fetch(window.__API_BASE__+'/api/client/orders-status', {credentials:'include'})
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (!data) return;
      const isReturning = data.orders && data.orders.length > 0;
      const note = document.getElementById('submitNote');
      const btn  = document.getElementById('submitBtn');
      if (note) {
        note.textContent = '🔒 Pay Now — full refund* in case you are not satisfied with delivery.';
      }
    }).catch(() => {});

  const urlSku = new URLSearchParams(window.top.location.search).get('task');
  if (urlSku) {
    const el = document.querySelector('[data-sku="'+urlSku+'"]');
    if (el) selectSku(urlSku, el);
  }

  // Dynamic Property Reel pricing based on tier selection
  var PR_TIER_INFO = {
    'hook':     { price: '₹999',   breakdown: 'Hook Reel · ~8 sec · 2 Frames · 9:16 for WhatsApp / Instagram' },
    'standard': { price: '₹1,599', breakdown: 'Standard Reel · ~30 sec · up to 5 Frames · full property walkthrough' },
    'showcase': { price: '₹2,499', breakdown: 'Showcase Reel · ~60 sec · up to 10 Frames · luxury listing quality' }
  };
  document.querySelectorAll('input[name="reel_tier"]').forEach(function(radio) {
    radio.addEventListener('change', function() {
      var priceEl = document.getElementById('pr-price-display');
      var breakdownEl = document.getElementById('pr-price-breakdown');
      var showcaseNote = document.getElementById('pr-showcase-note');
      if (!priceEl) return;
      var info = PR_TIER_INFO[this.value] || PR_TIER_INFO['hook'];
      priceEl.textContent = info.price;
      breakdownEl.textContent = info.breakdown;
      if (showcaseNote) showcaseNote.style.display = (this.value === 'showcase') ? 'block' : 'none';
      // BUG 8/9 fix: keep ribbon in sync with reel tier price
      var ribbon = document.getElementById('submitPriceRibbon');
      if (ribbon && currentSku === 'property_reel') ribbon.textContent = info.price;
    });
  });

  // ── Universal drag-drop + paste for all .upload-box elements ──
  var _lastHoveredBox = null;

  function _injectFilesIntoBox(box, files) {
    if (!files || files.length === 0) return;
    var input = box.querySelector('input[type=file]');
    if (!input) return;
    // Only accept image files (and pdf for moodboard)
    var accept = (input.getAttribute('accept') || '').toLowerCase();
    var filtered = Array.from(files).filter(function(f) {
      if (accept.indexOf('image/*') > -1 && !f.type.startsWith('image/')) return false;
      return true;
    });
    if (filtered.length === 0) return;
    var dt = new DataTransfer();
    if (input.multiple) {
      // Append to existing files if possible
      Array.from(input.files || []).forEach(function(f){ dt.items.add(f); });
    }
    filtered.forEach(function(f){ dt.items.add(f); });
    input.files = dt.files;
    // Trigger UI update
    if (input.multiple) {
      var listId = input.getAttribute('onchange') || '';
      var m = listId.match(/showMultiFile\(this,'([^']+)','([^']+)'\)/);
      if (m) { showMultiFile(input, m[1], m[2]); }
      else { box.classList.add('has-file'); }
    } else {
      var m2 = (input.getAttribute('onchange') || '').match(/showFile\(this,'([^']+)'/);
      if (m2) { showFile(input, m2[1]); }
      else { box.classList.add('has-file'); }
    }
    showToast('✓ ' + filtered.length + ' file' + (filtered.length > 1 ? 's' : '') + ' added', 'success');
  }

  function initUploadBox(box) {
    if (box._dndInit) return;
    box._dndInit = true;
    // Explicit click handler — opens file picker even if CSS overlay isn't covering the click target
    box.addEventListener('click', function(e) {
      var input = box.querySelector('input[type=file]');
      if (input && !input.disabled && e.target !== input) {
        e.stopPropagation();
        input.click();
      }
    });
    // Add hint text if not already there
    if (!box.querySelector('.upload-drag-hint')) {
      var hint = document.createElement('div');
      hint.className = 'upload-drag-hint';
      hint.textContent = 'drag & drop or paste from clipboard';
      box.appendChild(hint);
    }
    box.addEventListener('mouseenter', function() { _lastHoveredBox = box; });
    box.addEventListener('dragenter', function(e) { e.preventDefault(); box.classList.add('drag-over'); _lastHoveredBox = box; });
    box.addEventListener('dragover', function(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; box.classList.add('drag-over'); });
    box.addEventListener('dragleave', function(e) { if (!box.contains(e.relatedTarget)) box.classList.remove('drag-over'); });
    box.addEventListener('drop', function(e) {
      e.preventDefault();
      box.classList.remove('drag-over');
      var files = e.dataTransfer.files;
      if (files && files.length) {
        _injectFilesIntoBox(box, files);
      } else {
        // Handle drag of image from browser (dataTransfer.items with kind=file or URL)
        var items = e.dataTransfer.items;
        if (items) {
          for (var i = 0; i < items.length; i++) {
            if (items[i].kind === 'file') { _injectFilesIntoBox(box, [items[i].getAsFile()]); break; }
          }
        }
      }
    });
  }

  function initAllUploadBoxes() {
    document.querySelectorAll('.upload-box').forEach(initUploadBox);
  }

  // Paste from clipboard — targets last hovered box
  document.addEventListener('paste', function(e) {
    var box = _lastHoveredBox;
    if (!box) {
      // fall back to first visible upload box in the active SKU section
      var active = document.querySelector('.step-section.active .upload-box') || document.querySelector('.upload-box');
      box = active;
    }
    if (!box) return;
    var items = (e.clipboardData || window.clipboardData).items;
    var files = [];
    for (var i = 0; i < items.length; i++) {
      if (items[i].type.startsWith('image/')) {
        var f = items[i].getAsFile();
        if (f) {
          // Give it a sensible name
          var ext = f.type.split('/')[1] || 'png';
          Object.defineProperty(f, 'name', { value: 'pasted-image-' + Date.now() + '.' + ext });
          files.push(f);
        }
      }
    }
    if (files.length) {
      e.preventDefault();
      _injectFilesIntoBox(box, files);
    }
  });

  // Patch addVsPhotoRow and addPrPhotoRow to init new boxes after DOM insert
  var _origAddVsRow = addVsPhotoRow;
  addVsPhotoRow = function() { _origAddVsRow(); setTimeout(initAllUploadBoxes, 50); };
  var _origAddPrRow = addPrPhotoRow;
  addPrPhotoRow = function() { _origAddPrRow(); setTimeout(initAllUploadBoxes, 50); };
  initAllUploadBoxes();

  // Apply the SKU 4 marketplace lock when the form is shown (and on initial load).
  var _origSelectSku = selectSku;
  selectSku = function(sku, el) { _origSelectSku(sku, el); if (sku === 'bg_cleanup') applyBgLock(); if (sku === 'instagram_carousel') { var _f = document.querySelector('input[name=carousel_format]:checked'); if (typeof updateCarouselFormat === 'function') updateCarouselFormat(_f ? _f.value : 'Image + Text'); } };
  applyBgLock();
