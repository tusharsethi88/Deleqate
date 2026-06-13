// Final three SKU forms ported from order_wizard.html:
// brand_starter_kit, menu_design, podcast_reel. Fixed-price (no onPriceChange).
import { FormSection, FormGroup, Chips, CheckChips, UploadBox, PriceCard } from './widgets.jsx';

export function BrandStarterKitForm() {
  return (
    <>
      <FormSection title="🚀 Brand Details">
        <div className="grid-2">
          <FormGroup label="Business Name" required>
            <input type="text" name="business_name" className="form-control" placeholder="e.g. Bloom Wellness" required />
          </FormGroup>
          <FormGroup label="Industry / Type of Business" required>
            <input type="text" name="industry" className="form-control" placeholder="e.g. Online coaching, Restaurant, D2C skincare" required />
          </FormGroup>
        </div>
        <FormGroup label="3 Words that Describe Your Brand Personality" required>
          <input type="text" name="personality" className="form-control" placeholder="e.g. Trustworthy, Modern, Warm — or Playful, Bold, Fun" required />
        </FormGroup>
        <FormGroup label="Target Customer">
          <textarea name="target_customer" className="form-control" rows="2" placeholder="e.g. Working women 25–40 who want healthy meal options delivered at home" />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Colour Preference">
            <input type="text" name="color_preference" className="form-control" placeholder="e.g. Earthy tones, No preference, Must use Navy blue" />
          </FormGroup>
          <FormGroup label="Style Direction">
            <Chips name="style_direction" def="Minimal"
              options={['Minimal', 'Bold', 'Traditional', 'Luxury', 'Playful']} />
          </FormGroup>
        </div>
        <FormGroup label="Tagline">
          <input type="text" name="tagline" className="form-control" placeholder="Your existing tagline — or leave blank for us to create one" />
        </FormGroup>
        <FormGroup label="Brands / Competitors You Admire (optional)">
          <input type="text" name="reference_brands" className="form-control" placeholder="e.g. Mamaearth, Nykaa, Paper Boat — or any brand you like the look of" />
        </FormGroup>
      </FormSection>

      <FormSection title="🎁 What You Get!">
        <CheckChips name="deliverables"
          options={[
            ['Logo options (3 concepts)', 'Logo (3 concepts)'],
            ['Colour palette', 'Colour Palette'],
            ['Font pairing', 'Font Pairing'],
            ['Business card design', 'Business Card'],
            ['Social media banner', 'Social Media Banner'],
            ['Letterhead', 'Letterhead'],
          ]}
          defs={['Logo options (3 concepts)', 'Colour palette', 'Font pairing',
            'Business card design', 'Social media banner', 'Letterhead']} />
      </FormSection>

      <PriceCard amount="₹1,999" breakdown="Flat rate · all selected deliverables as PDF + PNG"
        sla="Delivered within 4 hours of assignment" />
    </>
  );
}

export function MenuDesignForm() {
  return (
    <>
      <FormSection title="🍽️ Business & Menu Details">
        <div className="grid-2">
          <FormGroup label="Business Name" required>
            <input type="text" name="business_name" className="form-control" placeholder="e.g. Chai & More Café" required />
          </FormGroup>
          <FormGroup label="Brand Colours">
            <input type="text" name="brand_colors" className="form-control" placeholder="e.g. Terracotta and cream, No preference" />
          </FormGroup>
        </div>
        <UploadBox name="logo_file" accept="image/*,.svg" icon="🖼️" label="Upload Logo (Recommended)"
          hint="PNG, SVG, JPG — transparent background preferred" style={{ marginBottom: '0.5rem' }} />
        <div style={{ marginBottom: '0.75rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', color: 'var(--gray-600)', background: '#FFF8E6', border: '1px solid #E8C84A', borderRadius: 'var(--radius)', padding: '0.5rem 0.75rem' }}>
            <input type="checkbox" name="create_logo" value="yes" style={{ width: 16, height: 16, accentColor: 'var(--gold)' }} />
            <span>I don't have a logo — <strong>please create one for me</strong> based on my brand colours and business name</span>
          </label>
        </div>
        <FormGroup label="Business URL(s)" required
          hint="The pilot will study these pages to extract your Brand DNA (tone, colors, audience, and palette) before building the menu.">
          <textarea name="business_urls" className="form-control" rows="2" placeholder="Paste any URL where your business is listed — website, Instagram, Facebook, LinkedIn, etc." required />
        </FormGroup>
        <FormGroup label="Menu Items + Prices" required>
          <textarea name="menu_items_text" className="form-control" rows="6" required
            placeholder={"Paste your menu here — organised by section:\n\nSTARTERS\nPaneer Tikka — ₹220\nVeg Spring Roll — ₹180\n\nMAINS\nDal Makhani — ₹280\nPaneer Butter Masala — ₹320\n\nDESSERTS\nGulab Jamun — ₹120"} />
        </FormGroup>
        <UploadBox name="existing_menu" accept="image/*,.pdf,.doc,.docx,.html,.htm,.txt" icon="📄"
          label="Upload Existing Menu (Optional — image, PDF, Word doc, HTML)" />
      </FormSection>

      <FormSection title="📐 Format & Style">
        <div className="grid-2">
          <FormGroup label="Menu Format">
            <Chips name="menu_format" def="A4 single page"
              options={['A4 single page', 'A4 double-sided', 'Trifold', 'Digital only']} />
          </FormGroup>
          <FormGroup label="Style">
            <Chips name="menu_style" def="modern"
              options={[['modern', 'Modern'], ['rustic', 'Rustic'], ['minimal', 'Minimal'], ['traditional', 'Traditional'], ['festive', 'Festive']]} />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Output Needed">
            <CheckChips name="output_format"
              options={[['Print-ready PDF', 'Print PDF'], ['Digital image (WhatsApp)', 'Digital / WhatsApp']]}
              defs={['Print-ready PDF', 'Digital image (WhatsApp)']} />
          </FormGroup>
          <FormGroup label="Dietary Icons (Veg / Non-veg markers)?">
            <Chips name="dietary_icons" def="no" options={[['yes', 'Yes'], ['no', 'No']]} />
          </FormGroup>
        </div>
        <FormGroup label="Special Callouts" style={{ marginBottom: 0 }}>
          <input type="text" name="special_callouts" className="form-control" placeholder="e.g. Highlight chef's specials, Add QR code for full menu, Add takeaway number" />
        </FormGroup>
      </FormSection>

      <PriceCard amount="₹799" breakdown="Flat rate · print PDF + digital image delivered"
        sla="Delivered within 3–4 hours of assignment" />
    </>
  );
}

export function PodcastReelForm() {
  return (
    <>
      <FormSection title="🎙️ Upload Audio File">
        <UploadBox name="audio_file" accept="audio/*,.mp3,.m4a,.wav,.aac" icon="🎙️"
          label="Upload Audio Recording" hint="MP3, M4A, WAV or AAC — any quality" />
        <UploadBox name="logo_file" accept="image/*" icon="🖼️" label="Show / Brand Logo (Optional)"
          style={{ marginTop: '0.75rem' }} />
      </FormSection>

      <FormSection title="📝 Episode Details">
        <div className="grid-2">
          <FormGroup label="Show Name" required>
            <input type="text" name="show_name" className="form-control" placeholder="e.g. The Founder's Table" required />
          </FormGroup>
          <FormGroup label="Total Recording Duration">
            <input type="text" name="recording_duration" className="form-control" placeholder="e.g. 45 minutes" />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Host Name">
            <input type="text" name="host_name" className="form-control" placeholder="Your name" />
          </FormGroup>
          <FormGroup label="Guest Name">
            <input type="text" name="guest_name" className="form-control" placeholder="Guest name or Solo" />
          </FormGroup>
        </div>
        <FormGroup label="Episode Topic" required>
          <input type="text" name="episode_topic" className="form-control" placeholder="e.g. How I built a ₹1Cr business with no investment" required />
        </FormGroup>
        <FormGroup label="3 Moments You Want Included (timestamps or descriptions)">
          <textarea name="preferred_moments" className="form-control" rows="2"
            placeholder={"1. Around 12:00 — the story about the first rejection\n2. Around 28:00 — the key insight on pricing\n3. Anywhere — the funniest moment"} />
        </FormGroup>
      </FormSection>

      <FormSection title="🎨 Output Preferences">
        <div className="grid-2">
          <FormGroup label="Output Format">
            <Chips name="output_format" def="audiogram"
              options={[['audiogram', 'Audiogram + Captions'], ['static_waveform', 'Static Image + Waveform']]} />
          </FormGroup>
          <FormGroup label="Target Platform">
            <Chips name="target_platform" def="Instagram"
              options={['Instagram', 'YouTube Shorts', 'LinkedIn']} />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Caption Style">
            <Chips name="caption_style" def="full"
              options={[['full', 'Full Captions'], ['keywords', 'Key Words Only']]} />
          </FormGroup>
          <FormGroup label="Brand Colours">
            <input type="text" name="brand_colors" className="form-control" placeholder="e.g. Dark green and gold, No preference" />
          </FormGroup>
        </div>
      </FormSection>

      <PriceCard amount="₹649" breakdown="Flat rate · 3 highlight clips · cleaned audio"
        sla="Delivered within 2–3 hours of assignment" />
    </>
  );
}
