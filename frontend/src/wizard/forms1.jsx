// Wizard forms — Real Estate cluster: Virtual Staging, Property Reel,
// Property Social Card. Direct ports of the template sections.
import { useState } from 'react';
import { FormSection, FormGroup, Chips, UploadBox, PriceCard } from './widgets.jsx';
import PhotoRows from './PhotoRows.jsx';

// ── VIRTUAL STAGING ─────────────────────────────────────────
export const VS_TIER = {
  starter: { base: 649, maxRooms: 2, extraPerRoom: 0 },
  full: { base: 799, maxRooms: 4, extraPerRoom: 100 },
};

export function vsTotal(tier, rooms) {
  const info = VS_TIER[tier] || VS_TIER.full;
  const extra = Math.max(0, rooms - info.maxRooms);
  return { total: info.base + extra * info.extraPerRoom, extra, info };
}

export function VirtualStagingForm({ onPriceChange }) {
  const [tier, setTier] = useState('full');
  const [rooms, setRooms] = useState(1);
  const { total, extra } = vsTotal(tier, rooms);

  function update(t = tier, r = rooms) {
    const { total } = vsTotal(t, r);
    onPriceChange?.(`₹${total.toLocaleString('en-IN')}`);
  }

  const breakdown = extra > 0
    ? `₹${VS_TIER[tier].base} base + ${extra} × ₹100 extra room${extra > 1 ? 's' : ''}`
    : (tier === 'starter' ? 'Flat rate · 2 rooms · one render per room' : 'Flat rate · up to 4 rooms staged · one render per room');

  const tierCard = (value, name, sub, price) => (
    <div className="chip" style={{ flex: 1, minWidth: 180 }}>
      <input type="radio" name="vs_tier" value={value} id={`vs-tier-${value}`} checked={tier === value}
        onChange={() => { setTier(value); update(value); }} />
      <label htmlFor={`vs-tier-${value}`} style={{ display: 'block', padding: '0.75rem 1rem' }}>
        <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{name}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.2rem' }}>{sub}</div>
        <div style={{ fontWeight: 700, color: 'var(--navy)', marginTop: '0.3rem' }}>{price}</div>
      </label>
    </div>
  );

  return (
    <>
      <FormSection title="🏠 Choose Your Package">
        <div className="chips" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
          {tierCard('starter', 'Starter', '2 rooms · one render per room', '₹649')}
          {tierCard('full', 'Full Staging', 'up to 4 rooms · ₹100/extra room', '₹799')}
        </div>
        <div style={{ marginTop: '0.5rem', fontSize: '0.78rem', color: 'var(--gray-500)' }}>₹799 covers up to 4 rooms. Each additional room is charged at ₹100/room.</div>
        {extra > 0 && (
          <div style={{ marginTop: '0.5rem', padding: '0.5rem 0.75rem', background: '#fef9ec', borderLeft: '3px solid #f59e0b', borderRadius: 4, fontSize: '0.78rem', color: '#92400e' }}>
            ⚠ Surcharge: {extra} extra room{extra > 1 ? 's' : ''} × ₹100 = +₹{extra * 100}
          </div>
        )}
      </FormSection>

      <FormSection title="📷 Upload Room Photos" sub="Label each space — pilot stages each one separately">
        <PhotoRows kind="vs" onCountChange={r => { setRooms(r); update(tier, r); }} />
        <div style={{ fontSize: '0.72rem', color: 'var(--gray-400)', marginTop: '0.6rem' }}>
          💡 POV B (second angle of same room) helps the AI understand geometry — <strong style={{ color: '#92400e' }}>strongly recommended for under-construction / shell spaces.</strong>
        </div>
      </FormSection>

      <FormSection title="🎨 Global Style Reference" sub="Optional — global fallback moodboard">
        <UploadBox name="moodboard_file" accept="image/*,.pdf" icon="🎨" label="Upload Moodboard"
          hint="Pinterest board screenshot, magazine clipping, or reference image" />
      </FormSection>

      <FormSection title="🏢 Property Details">
        <div className="grid-2">
          <FormGroup label="Property Type">
            <Chips name="property_type" def="Residential"
              options={[['Residential', 'Residential'], ['Office', 'Office'], ['Restaurant / Café', 'Restaurant'], ['Hotel Room', 'Hotel'], ['Retail Store', 'Retail']]} />
          </FormGroup>
          <FormGroup label="Property Stage">
            <Chips name="property_stage" def="Finished"
              options={[['Finished', 'Finished / Ready'], ['Under Construction', 'Under Construction'], ['Shell / Bare Concrete', 'Shell / Bare Concrete']]} />
          </FormGroup>
        </div>
      </FormSection>

      <FormSection title="🛋️ Staging Preferences">
        <FormGroup label="Design Style">
          <Chips name="style" def="Warm Contemporary"
            options={['Modern Luxury', 'Warm Contemporary', 'Minimalist', 'Traditional Indian', 'Scandinavian', 'Bohemian']} />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Target Buyer" style={{ marginBottom: 0 }}>
            <Chips name="buyer_profile" def="Family"
              options={[['HNI', 'HNI'], ['HNI COUPLE', 'HNI Couple'], ['Young Professional', 'Young Professional'], ['Family', 'Family'], ['Investor', 'Investor'], ['NRI', 'NRI']]} />
          </FormGroup>
          <FormGroup label="Special Notes" optional style={{ marginBottom: 0 }}>
            <input type="text" name="special_notes" className="form-control" placeholder="e.g. Put LED in front of bed, prefer dark wood, no TV on wall" />
          </FormGroup>
        </div>
      </FormSection>

      <PriceCard amount={`₹${total.toLocaleString('en-IN')}`} breakdown={breakdown}
        sla="Delivered within 3–5 hours of assignment" />
    </>
  );
}

// ── PROPERTY REEL ───────────────────────────────────────────
export const PR_TIER_INFO = {
  hook: { price: '₹999', breakdown: 'Hook Reel · ~8 sec · 2 Frames · 9:16 for WhatsApp / Instagram' },
  standard: { price: '₹1,599', breakdown: 'Standard Reel · ~30 sec · up to 5 Frames · full property walkthrough' },
  showcase: { price: '₹2,499', breakdown: 'Showcase Reel · ~60 sec · up to 10 Frames · luxury listing quality' },
};

export function PropertyReelForm({ onPriceChange }) {
  const [tier, setTier] = useState('hook');
  const info = PR_TIER_INFO[tier];

  const tierCard = (value, name, sub, price) => (
    <div className="chip" style={{ flex: 1, minWidth: 180 }}>
      <input type="radio" name="reel_tier" value={value} id={`pr-tier-${value}`} checked={tier === value}
        onChange={() => { setTier(value); onPriceChange?.(PR_TIER_INFO[value].price); }} />
      <label htmlFor={`pr-tier-${value}`} style={{ display: 'block', padding: '0.75rem 1rem' }}>
        <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{name}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.2rem' }}>{sub}</div>
        <div style={{ fontWeight: 700, color: 'var(--navy)', marginTop: '0.3rem' }}>{price}</div>
      </label>
    </div>
  );

  return (
    <>
      <FormSection title="🎬 Choose Your Reel">
        <div className="chips" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
          {tierCard('hook', 'Hook Reel', '~8 sec · 2 Frames · WhatsApp / Stories teaser', '₹999')}
          {tierCard('standard', 'Standard Reel', '~30 sec · up to 5 Frames · full walkthrough', '₹1,599')}
          {tierCard('showcase', 'Showcase Reel', '~60 sec · up to 10 Frames · luxury listing quality', '₹2,499')}
        </div>
        {tier === 'showcase' && (
          <div style={{ marginTop: '0.6rem', padding: '0.5rem 0.75rem', background: '#fef9ec', borderLeft: '3px solid #f59e0b', borderRadius: 4, fontSize: '0.78rem', color: '#92400e' }}>
            ⚡ Showcase Reel: pilot will use Google Flow (Veo 3.1) for premium per-clip generation.
          </div>
        )}
      </FormSection>

      <FormSection title="📷 Upload Property Photos" sub="Label each area — pilot uses these to sequence the reel">
        <PhotoRows kind="pr" />
        <div style={{ fontSize: '0.72rem', color: 'var(--gray-400)', marginTop: '0.5rem' }}>
          Hook needs 5 photos · Standard 8–12 · Showcase 12–16. Label each accurately. 💡 POV B helps AI understand room geometry — <strong style={{ color: '#92400e' }}>recommended for empty / shell properties.</strong>
        </div>
      </FormSection>

      <FormSection title="🏠 Property Details">
        <div className="grid-2">
          <FormGroup label="Property Name (if any)">
            <input type="text" name="property_name" className="form-control" placeholder="e.g. Sunrise Heights, The Meadows" />
          </FormGroup>
          <FormGroup label="Location" required>
            <input type="text" name="location" className="form-control" placeholder="e.g. Sector 62, Noida" required />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Property Size">
            <Chips name="bhk_size" def="2BHK"
              options={[['1BHK', '1 BHK'], ['2BHK', '2 BHK'], ['3BHK', '3 BHK'], ['4BHK', '4 BHK'], ['Villa', 'Villa']]} />
          </FormGroup>
          <FormGroup label="Property Type">
            <Chips name="property_type" def="Residential"
              options={[['Residential', 'Residential'], ['Office', 'Office'], ['Restaurant / Café', 'Restaurant'], ['Hotel Room', 'Hotel'], ['Retail Store', 'Retail']]} />
          </FormGroup>
        </div>
        <FormGroup label="Key Selling Points" required>
          <textarea name="selling_points" className="form-control" rows={2}
            placeholder="e.g. 1250 sqft, Ready to move, Near metro, Sea view, Price on request" required />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Contact Name (end frame)" required>
            <input type="text" name="contact_name" className="form-control" placeholder="Your name or agency name" required />
          </FormGroup>
          <FormGroup label="Contact Number" required>
            <input type="text" name="contact_number" className="form-control" placeholder="+91 98765 43210" required />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Tone">
            <Chips name="tone" def="Family" options={['Luxury', 'Affordable', 'Family', 'Investment']} />
          </FormGroup>
          <FormGroup label="Background Music">
            <Chips name="music" def="soft" options={[['soft', 'Soft / Ambient'], ['energetic', 'Energetic'], ['none', 'No Music']]} />
          </FormGroup>
        </div>
        <FormGroup label="Voiceover / Text Overlay" style={{ marginBottom: 0 }}>
          <Chips name="voiceover" def="no" options={[['yes', 'Yes (text overlay)'], ['no', 'No — visuals only']]} />
        </FormGroup>
      </FormSection>

      <FormSection title="🎨 Property Condition & Style" sub="Used to build accurate AI prompts — answer honestly">
        <div className="grid-2">
          <FormGroup label="Furnished Status" required
            hint="Affects AI video style — unfurnished properties get architectural treatment, not interior decor treatment">
            <Chips name="furnished_status" def="Fully Furnished"
              options={[['Fully Furnished', 'Fully Furnished'], ['Semi-Furnished', 'Semi-Furnished'], ['Unfurnished', 'Unfurnished'], ['Shell/Under Construction', 'Shell / UC']]} />
          </FormGroup>
          <FormGroup label="Interior Style">
            <Chips name="interior_style" def="Modern/Contemporary"
              options={[['Modern/Contemporary', 'Modern'], ['Minimalist', 'Minimalist'], ['Traditional/Classic', 'Traditional'], ['Industrial', 'Industrial']]} />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Listing Price Range">
            <Chips name="price_bracket" def="₹50L–1Cr"
              options={['Under ₹50L', '₹50L–1Cr', '₹1–3Cr', '₹3Cr+', 'Commercial']} />
          </FormGroup>
          <FormGroup label="Special Instructions" optional>
            <input type="text" name="special_note" className="form-control"
              placeholder="e.g. Ignore damaged ceiling, focus on sea view, avoid kitchen corner" />
          </FormGroup>
        </div>
      </FormSection>

      {/* platform hidden — pilot selects their tool in the pilot dashboard */}
      <input type="hidden" name="platform" value="kling" />

      <PriceCard amount={info.price} breakdown={info.breakdown} sla="Delivered within 3–5 hours of assignment" />
    </>
  );
}

// ── PROPERTY SOCIAL CARD PACK ───────────────────────────────
export function PropertySocialCardForm() {
  return (
    <>
      <FormSection title="📸 Property Photo" sub="Best exterior or key interior — used as hero image">
        <UploadBox name="property_photo" accept="image/*" icon="🏠" label="Upload Hero Property Photo"
          hint="JPG or PNG — best quality available" />
      </FormSection>
      <FormSection title="🏠 Property Information">
        <div className="grid-2">
          <FormGroup label="Property Name / Type" required>
            <input type="text" name="property_name" className="form-control" placeholder="e.g. 3BHK Apartment, Sunrise Villa" required />
          </FormGroup>
          <FormGroup label="Location" required>
            <input type="text" name="location" className="form-control" placeholder="e.g. Bandra West, Mumbai" required />
          </FormGroup>
        </div>
        <FormGroup label="3 Key Highlights" required hint="These appear as the 3 bullet points on both cards.">
          <textarea name="highlights" className="form-control" rows={2}
            placeholder="e.g. Sea view from balcony · 2 min from metro · Ready to move in" required />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Asking Price" required>
            <input type="text" name="asking_price" className="form-control" placeholder="e.g. ₹1.85 Cr · Price on request" required />
          </FormGroup>
          <FormGroup label="Contact Number (on card)" required>
            <input type="text" name="contact_number" className="form-control" placeholder="+91 98765 43210" required />
          </FormGroup>
        </div>
        <FormGroup label="Contact Name" style={{ marginBottom: 0 }}>
          <input type="text" name="contact_name" className="form-control" placeholder="Your name or agency name" />
        </FormGroup>
      </FormSection>
      <FormSection title="🎨 Brand / Style">
        <div className="grid-2">
          <FormGroup label="Card Style" style={{ marginBottom: 0 }}>
            <Chips name="card_style" def="Modern"
              options={[['Modern', 'Modern'], ['Luxury', 'Luxury'], ['Minimal', 'Minimal'], ['Bold', 'Bold / Colourful']]} />
          </FormGroup>
          <FormGroup label="Brand Colours" optional style={{ marginBottom: 0 }}>
            <input type="text" name="brand_colors" className="form-control" placeholder="e.g. Navy #1A3A5C · Gold #F5A623" />
          </FormGroup>
        </div>
        <div style={{ marginTop: '1rem' }}>
          <UploadBox name="logo_file" accept="image/*,.svg" icon="🏷️" label="Logo (Optional)"
            hint="PNG or SVG with transparent background" />
        </div>
      </FormSection>
      <PriceCard amount="₹499"
        breakdown="Flat rate · 2 assets delivered: 1:1 Square (WhatsApp Card & Instagram Post) + 9:16 Vertical (WhatsApp & Instagram Story)"
        sla="Delivered within 1–under 4 hours of assignment" />
    </>
  );
}
