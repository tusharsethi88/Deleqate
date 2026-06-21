// Wizard forms — E-commerce cluster: Background Cleanup, Product Listing,
// Product Lifestyle Mockup.
import { useState } from 'react';
import { FormSection, FormGroup, Chips, CheckChips, UploadBox, PriceCard, QtyRow } from './widgets.jsx';

// Controlled radio-chip group — lets us force / lock selections for the
// marketplace smart-branch (the shared Chips widget is uncontrolled).
let _bgSeq = 0;
function ChipGroup({ value, onChange, options, disabled }) {
  const base = useState(() => `bgc${++_bgSeq}`)[0];
  return (
    <div className="chips">
      {options.map((o, i) => {
        const [val, label] = Array.isArray(o) ? o : [o, o];
        const id = `${base}-${i}`;
        return (
          <div className="chip" key={val}>
            <input type="radio" id={id} checked={val === value} disabled={disabled}
              onChange={() => onChange(val)} />
            <label htmlFor={id} style={disabled ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}>{label}</label>
          </div>
        );
      })}
    </div>
  );
}

// ── BACKGROUND CLEANUP (SKU 4) ──────────────────────────────
export function BgCleanupForm({ onPriceChange }) {
  const [count, setCount] = useState(5);
  const [finalUse, setFinalUse] = useState('Amazon / Flipkart');
  const [background, setBackground] = useState('white');
  const [shadow, setShadow] = useState('natural');
  const [outputFormat, setOutputFormat] = useState('PNG');
  const [customHex, setCustomHex] = useState('');

  const total = 79 * count;
  const set = c => { setCount(c); onPriceChange?.(`₹${(79 * c).toLocaleString('en-IN')}`); };

  // Smart branch — marketplace compliance lock (the headline feature)
  const marketplace = finalUse === 'Amazon / Flipkart';
  const bgVal = marketplace ? 'white' : background;
  const shadowVal = marketplace ? 'none' : shadow;
  const fmtVal = marketplace ? 'JPG' : outputFormat;

  return (
    <>
      <FormSection title="📦 Upload Product Images">
        <UploadBox name="product_photos" accept="image/*" multiple required icon="📦"
          label="Upload Product Photos (min 5)" hint="JPG or PNG — any background, any angle" />
      </FormSection>

      <FormSection title="🛒 Where will you use these?">
        <FormGroup required style={{ marginBottom: marketplace ? '0.75rem' : 0 }}
          hint="Pick the destination — we auto-apply the right compliance rules.">
          <ChipGroup value={finalUse} onChange={setFinalUse}
            options={['Amazon / Flipkart', 'Shopify / D2C', 'Instagram / Ads', 'Other']} />
        </FormGroup>
        {marketplace && (
          <div style={{ borderLeft: '3px solid var(--gold)', background: '#fffbe9',
            fontSize: '0.78rem', padding: '0.6rem 0.8rem', borderRadius: 6, color: '#735c00' }}>
            🔒 <strong>Marketplace rule applied.</strong> Amazon &amp; Flipkart require a pure white
            background, no shadow, and JPG output. We've locked these so your listing isn't rejected.
            Choose another destination to unlock them.
          </div>
        )}
      </FormSection>

      <FormSection title="🎨 Output Preferences">
        <div className="grid-2">
          <FormGroup label="Background" required>
            <ChipGroup value={bgVal} onChange={setBackground} disabled={marketplace}
              options={[['white', 'Pure White'], ['transparent', 'Transparent PNG'],
                ['light grey', 'Light Grey Studio'], ['custom', 'Custom (hex)']]} />
            {bgVal === 'custom' && !marketplace && (
              <input type="text" name="background_custom" className="form-control" style={{ marginTop: 8 }}
                value={customHex} onChange={e => setCustomHex(e.target.value)}
                placeholder="#RRGGBB  e.g. #EAE5DF" />
            )}
          </FormGroup>
          <FormGroup label="Shadow" required>
            <ChipGroup value={shadowVal} onChange={setShadow} disabled={marketplace}
              options={[['none', 'None (hard cutout)'], ['natural', 'Natural Soft Shadow'],
                ['reflection', 'Reflection']]} />
          </FormGroup>
        </div>
        <FormGroup label="Output Format">
          <ChipGroup value={fmtVal} onChange={setOutputFormat} disabled={marketplace} options={['PNG', 'JPG']} />
        </FormGroup>
      </FormSection>

      {/* hidden fields carry the effective (possibly locked) values to the backend */}
      <input type="hidden" name="final_use" value={finalUse} />
      <input type="hidden" name="background_type" value={bgVal} />
      <input type="hidden" name="shadow" value={shadowVal} />
      <input type="hidden" name="output_format" value={fmtVal} />

      <FormSection title="📝 Anything specific?" sub="Optional">
        <FormGroup style={{ marginBottom: 0 }}
          hint="💡 Marketplace output is delivered at 2000×2000px JPG. Other destinations at 1200×1200px min.">
          <textarea name="special_instructions" className="form-control" rows={2}
            placeholder="e.g. Reflective surface — be careful with edges. Keep label text sharp." />
        </FormGroup>
      </FormSection>

      <FormSection title="🔢 Number of Images">
        <QtyRow value={count} min={5} onChange={set} suffix="images · ₹79 each · min 5" />
        <input type="hidden" name="image_count" value={count} />
        <PriceCard amount={`₹${total.toLocaleString('en-IN')}`}
          breakdown={`₹79 × ${count} image${count > 1 ? 's' : ''}`}
          sla="Delivered within 1 hour of assignment" />
      </FormSection>
    </>
  );
}

// ── PRODUCT LISTING ─────────────────────────────────────────
export function ProductListingForm({ onPriceChange }) {
  const [count, setCount] = useState(1);
  const [d2c, setD2c] = useState(false);
  const total = 199 * count;
  const set = c => { setCount(c); onPriceChange?.(`₹${(199 * c).toLocaleString('en-IN')}`); };

  return (
    <>
      <FormSection title="📦 Product Details">
        <div style={{ marginBottom: '1rem' }}>
          <UploadBox name="product_photo" accept="image/*" icon="📷" label="Upload Product Photo" hint="JPG or PNG — any angle" />
        </div>
        <div className="grid-2">
          <FormGroup label="Product Name" required>
            <input type="text" name="product_name" className="form-control" placeholder="e.g. BRF Stainless Steel Water Bottle" required />
          </FormGroup>
          <FormGroup label="Brand Name">
            <input type="text" name="brand_name" className="form-control" placeholder="e.g. BRF, Generic, Private Label" />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Category">
            <input type="text" name="category" className="form-control" placeholder="e.g. Kitchen & Dining, Sports, Beauty" />
          </FormGroup>
          <FormGroup label="Price Point">
            <input type="text" name="price_point" className="form-control" placeholder="e.g. ₹499" />
          </FormGroup>
        </div>
        <FormGroup label="Key Features (5–10 points)" required>
          <textarea name="key_features" className="form-control" rows={3} required
            placeholder={"List each feature on a new line:\n1000ml capacity\nBPA-free stainless steel\nKeeps cold 24 hrs / hot 12 hrs\nLeak-proof lid"} />
        </FormGroup>
        <FormGroup label="Specifications (dimensions, weight, colours, variants)">
          <textarea name="specifications" className="form-control" rows={2}
            placeholder="e.g. 280mm tall, 500g, Available in Black / Silver / Red, Pack of 1" />
        </FormGroup>
        <FormGroup label="Target Buyer">
          <input type="text" name="target_buyer" className="form-control" placeholder="e.g. Office-goers, gym enthusiasts, students" />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Platforms">
            <CheckChips name="platform[]" defs={['Amazon']}
              options={[['Amazon', 'Amazon'], ['Flipkart', 'Flipkart'], ['Meesho', 'Meesho'], ['D2C Website', 'D2C Site']]}
              onChange={(v, checked) => { if (v === 'D2C Website') setD2c(checked); }} />
            {d2c && (
              <FormGroup label="D2C Website URL" style={{ marginTop: '1rem' }}>
                <input type="text" name="d2c_website_url" className="form-control" placeholder="e.g. www.yourbrand.com" />
              </FormGroup>
            )}
          </FormGroup>
          <FormGroup label="Primary Keyword (optional)">
            <input type="text" name="primary_keyword" className="form-control" placeholder="e.g. stainless steel water bottle insulated" />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="New listing or updating existing?">
            <Chips name="listing_type" def="new" options={[['new', 'New Listing'], ['update', 'Updating Existing']]} />
          </FormGroup>
          <FormGroup label="Competitor Product URL" optional>
            <input type="text" name="competitor_url" className="form-control" placeholder="e.g. amazon.in/dp/B0XXXXXXX" />
          </FormGroup>
        </div>
      </FormSection>
      <FormSection title="🔢 Number of Products">
        <QtyRow value={count} min={1} onChange={set} suffix="products · ₹199 each" />
        <input type="hidden" name="product_count" value={count} />
        <PriceCard amount={`₹${total.toLocaleString('en-IN')}`}
          breakdown={`₹199 × ${count} product${count > 1 ? 's' : ''}`}
          sla="Delivered within 1–under 4 hours of assignment" />
      </FormSection>
    </>
  );
}

// ── PRODUCT MOCKUP (SKU 6) ──────────────────────────────────
// Low-friction intake. The pilot's LLM reads the product's material, finish,
// colour, proportions and scale straight from the uploaded photo, so we no
// longer ask the client for those — we only collect creative *intent*.
const PM_CATEGORIES = ['Skincare / Beauty', 'Food & Beverage', 'Home Fragrance / Candles',
  'Supplements / Wellness', 'Electronics / Gadgets', 'Apparel / Accessories', 'Baby / Kids',
  'Kitchen / Cookware', 'Stationery / Office', 'Lighting / Lamps', 'Furniture / Home Décor', 'Other'];

// Category → curated scene ideas. Tapping one fills the (still editable) scene
// box, so a blank field becomes a good default — lifts quality AND cuts typing.
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

export function ProductMockupForm({ onPriceChange }) {
  const [count, setCount] = useState(1);
  const [category, setCategory] = useState('');
  const [scene, setScene] = useState('');
  const total = 299 * count;
  const set = c => { setCount(c); onPriceChange?.(`₹${(299 * c).toLocaleString('en-IN')}`); };
  const sceneChips = PM_SCENES[category] || [];

  return (
    <>
      <FormSection title="📦 Upload Product Photo">
        <UploadBox name="product_photos" accept="image/*" multiple required icon="📦"
          label="Upload Product Photo(s)" hint="Clear, sharp shot — white background preferred. The pilot reads material, finish & scale straight from this." />
      </FormSection>

      <FormSection title="🌅 The Scene" sub="— tell us where it should live; we handle the rest">
        <div className="grid-2">
          <FormGroup label="Product Name" required>
            <input type="text" name="product_name" className="form-control" placeholder="e.g. BRF Water Bottle" required />
          </FormGroup>
          <FormGroup label="Product Category" required>
            <Chips name="product_category" options={PM_CATEGORIES} required onChange={setCategory} />
          </FormGroup>
        </div>

        <FormGroup label="Scene / Setting" required
          hint={category ? 'Tap a suggestion or type your own.' : undefined}>
          {!category && (
            <span style={{ fontSize: '0.8rem', color: '#9CA3AF', padding: '6px 0', display: 'inline-block' }}>
              ← Pick a category above to see scene ideas
            </span>
          )}
          {category && (
            <>
              <div className="chips" style={{ marginBottom: 8 }}>
                {sceneChips.map(s => (
                  <button type="button" key={s} onClick={() => setScene(s)}
                    style={{
                      border: scene === s ? '1.5px solid var(--gold)' : '1px solid #D7DEE6',
                      background: scene === s ? '#fffbe9' : '#fff', color: '#374151',
                      borderRadius: 16, padding: '5px 12px', fontSize: '0.82rem',
                      cursor: 'pointer', marginRight: 6, marginBottom: 6,
                    }}>{s}</button>
                ))}
              </div>
              <input type="text" className="form-control" required
                placeholder="Describe the scene (e.g. Rooftop café at sunset, Boho living room)…"
                value={scene} onChange={e => setScene(e.target.value)} />
            </>
          )}
          <input type="hidden" name="scene_setting" value={scene} />
        </FormGroup>

        <div className="grid-2">
          <FormGroup label="Mood">
            <Chips name="mood" def="Minimal & Clean"
              options={['Cozy & Warm', 'Energetic', 'Minimal & Clean', 'Luxury', 'Playful']} />
          </FormGroup>
          <FormGroup label="Output Ratio / Platform">
            <Chips name="output_ratio" def="1:1"
              options={[['1:1', '1:1 Square (Amazon)'], ['4:5', '4:5 Portrait (Instagram)'], ['9:16', '9:16 Story/Reel'], ['16:9', '16:9 Landscape (Banner)']]} />
          </FormGroup>
        </div>
      </FormSection>

      <FormSection title="➕ Optional" sub="— leave blank and the pilot will decide what looks best">
        <div className="grid-2">
          <FormGroup label="Anything to avoid in the scene?">
            <input type="text" name="avoid_elements" className="form-control" placeholder="e.g. No people, no competing brands, no alcohol" />
          </FormGroup>
          <FormGroup label="Brand Colours" hint="Scene will complement these">
            <input type="text" name="brand_colours" className="form-control" placeholder="e.g. Navy #1A3A5C and Gold #F5A623" />
          </FormGroup>
        </div>
        <FormGroup label="Product / Website URL" optional style={{ marginBottom: 0 }}
          hint="Helps the pilot match your brand's look & feel">
          <input type="url" name="product_url" className="form-control" placeholder="e.g. https://amazon.in/dp/B0XXXXXXX" />
        </FormGroup>
      </FormSection>

      <FormSection title="🔢 Number of Mockups">
        <QtyRow value={count} min={1} onChange={set} suffix="mockups · ₹299 each" />
        <input type="hidden" name="mockup_count" value={count} />
        <PriceCard amount={`₹${total.toLocaleString('en-IN')}`}
          breakdown={`₹299 × ${count} mockup${count > 1 ? 's' : ''}`}
          sla="Delivered within 1.5–2.5 hours of assignment" />
      </FormSection>
    </>
  );
}
