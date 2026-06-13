// Wizard forms — E-commerce cluster: Background Cleanup, Product Listing,
// Product Lifestyle Mockup.
import { useState } from 'react';
import { FormSection, FormGroup, Chips, CheckChips, UploadBox, PriceCard, QtyRow } from './widgets.jsx';

// ── BACKGROUND CLEANUP ──────────────────────────────────────
export function BgCleanupForm({ onPriceChange }) {
  const [count, setCount] = useState(5);
  const total = 79 * count;
  const set = c => { setCount(c); onPriceChange?.(`₹${(79 * c).toLocaleString('en-IN')}`); };

  return (
    <>
      <FormSection title="📦 Upload Product Images">
        <UploadBox name="product_photos" accept="image/*" multiple icon="📦"
          label="Upload Product Photos (min 5)" hint="JPG or PNG — any background, any angle" />
      </FormSection>
      <FormSection title="🎨 Output Preferences">
        <div className="grid-2">
          <FormGroup label="Background">
            <Chips name="background_type" def="white"
              options={[['white', 'Pure White'], ['light grey', 'Light Grey'], ['transparent', 'Transparent PNG']]} />
          </FormGroup>
          <FormGroup label="Shadow">
            <Chips name="shadow" def="none"
              options={[['none', 'No Shadow'], ['natural', 'Natural Shadow'], ['drop', 'Drop Shadow']]} />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Output Format">
            <Chips name="output_format" def="PNG" options={['JPG', 'PNG']} />
          </FormGroup>
          <FormGroup label="Final Use">
            <Chips name="final_use" def="Amazon / Flipkart" options={['Amazon / Flipkart', 'Website', 'Print']} />
          </FormGroup>
        </div>
      </FormSection>
      <FormSection title="📝 Special Instructions" sub="Optional">
        <FormGroup style={{ marginBottom: 0 }}
          hint="💡 Amazon/Flipkart output will be delivered at 2000×2000px. Website at 1200×1200px. Print at 300 DPI.">
          <textarea name="special_instructions" className="form-control" rows={2}
            placeholder="e.g. Product has reflective surface — be careful with edges. Keep label text sharp. Preserve all fine detail on cap." />
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

// ── PRODUCT MOCKUP ──────────────────────────────────────────
const PM_CATEGORIES = ['Skincare / Beauty', 'Food & Beverage', 'Home Fragrance / Candles',
  'Supplements / Wellness', 'Electronics / Gadgets', 'Apparel / Accessories', 'Baby / Kids',
  'Kitchen / Cookware', 'Stationery / Office', 'Lighting / Lamps', 'Furniture / Home Décor', 'Other'];

export function ProductMockupForm({ onPriceChange }) {
  const [count, setCount] = useState(1);
  const [category, setCategory] = useState('');
  const [scene, setScene] = useState('');
  const total = 299 * count;
  const set = c => { setCount(c); onPriceChange?.(`₹${(299 * c).toLocaleString('en-IN')}`); };

  return (
    <>
      <FormSection title="📦 Upload Product Photo">
        <UploadBox name="product_photos" accept="image/*" multiple icon="📦"
          label="Upload Product Photo(s)" hint="White background preferred but not required" />
      </FormSection>
      <FormSection title="🌅 Scene Preferences">
        <div className="grid-2">
          <FormGroup label="Product Name" required>
            <input type="text" name="product_name" className="form-control" placeholder="e.g. BRF Water Bottle" required />
          </FormGroup>
          <FormGroup label="Product Description (one line)">
            <input type="text" name="product_desc" className="form-control" placeholder="e.g. Insulated stainless steel water bottle" />
          </FormGroup>
        </div>
        <FormGroup label="Product Category" required>
          <Chips name="product_category" options={PM_CATEGORIES} required onChange={setCategory} />
        </FormGroup>
        <FormGroup label="Product URL" optional>
          <input type="url" name="product_url" className="form-control" placeholder="e.g. https://amazon.in/dp/B0XXXXXXX" />
        </FormGroup>
        <FormGroup label="Scene / Setting">
          {!category && (
            <span style={{ fontSize: '0.8rem', color: '#9CA3AF', padding: '6px 0', display: 'inline-block' }}>
              ← Select a product category above to see scene options
            </span>
          )}
          <input type="hidden" name="scene_setting" value={scene} />
          {category && (
            <input type="text" className="form-control"
              placeholder="Describe the scene / setting (e.g. Rooftop at sunset, Boho living room)..."
              value={scene} onChange={e => setScene(e.target.value)} />
          )}
        </FormGroup>
        <FormGroup label="Mood">
          <Chips name="mood" def="Minimal & Clean"
            options={['Cozy & Warm', 'Energetic', 'Minimal & Clean', 'Luxury', 'Playful']} />
        </FormGroup>
        <FormGroup label="Target Audience">
          <input type="text" name="target_audience" className="form-control" placeholder="e.g. Young professionals, moms, fitness enthusiasts" />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Product Material & Finish" hint="Helps AI preserve design accurately">
            <input type="text" name="product_material" className="form-control" placeholder="e.g. Matte black ABS plastic, glossy silver stainless steel" />
          </FormGroup>
          <FormGroup label="Brand Colours" hint="Optional — scene will complement">
            <input type="text" name="brand_colours" className="form-control" placeholder="e.g. Navy #1A3A5C and Gold #F5A623" />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Output Ratio / Platform">
            <Chips name="output_ratio" def="1:1"
              options={[['1:1', '1:1 Square (Amazon)'], ['4:5', '4:5 Portrait (Instagram)'], ['9:16', '9:16 Story/Reel'], ['16:9', '16:9 Landscape (Banner)']]} />
          </FormGroup>
          <FormGroup label="Elements to Avoid in Scene">
            <input type="text" name="avoid_elements" className="form-control" placeholder="e.g. No alcohol, no competing brand products, no people" />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Lighting Direction / Environment" style={{ marginBottom: 0 }}>
            <input type="text" name="lighting_direction" className="form-control" placeholder="e.g. Studio overhead lighting, harsh midday sun from left" />
          </FormGroup>
          <FormGroup label="Scale Reference" style={{ marginBottom: 0 }}>
            <input type="text" name="scale_reference" className="form-control" placeholder="e.g. Product should look 10 inches tall next to a coffee cup" />
          </FormGroup>
        </div>
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
