// Wizard forms — SMB Visual Content: Instagram Carousel, Brand Demo Video,
// Announcement Pack.
import { FormSection, FormGroup, Chips, UploadBox, PriceCard } from './widgets.jsx';

// ── INSTAGRAM CAROUSEL (SKU 7) — 9 essential fields ─────────
export function InstagramCarouselForm() {
  return (
    <>
      <FormSection title="🏷 Brand Basics">
        <div className="grid-2">
          <FormGroup label="Brand / Business Name" required>
            <input type="text" name="brand_name" className="form-control" placeholder="e.g. GlowUp Skincare" required />
          </FormGroup>
          <FormGroup label="Brand Colours" hint="Leave blank to pull from your logo">
            <input type="text" name="brand_colours" className="form-control" placeholder="e.g. Soft peach + cream + gold · or #F5A623" />
          </FormGroup>
        </div>
        <UploadBox name="logo_file" accept="image/*,.svg" icon="🖼️" label="Upload Logo (Optional)"
          hint="PNG with transparent background preferred — sets your brand colours" />
      </FormSection>

      <FormSection title="💡 Carousel Brief">
        <FormGroup label="Goal of this carousel" required>
          <Chips name="goal" def="Educate / Tips"
            options={['Educate / Tips', 'Promote Product / Offer', 'Tell Brand Story', 'Announce', 'Drive to Link']} />
        </FormGroup>
        <FormGroup label="Topic — what's it about?" required>
          <input type="text" name="carousel_topic" className="form-control" required
            placeholder="e.g. 5 skincare mistakes that age your skin · How our coaching programme works" />
        </FormGroup>
        <FormGroup label="Key points to cover" required
          hint="Up to 5 — each becomes one slide. Fill at least the first.">
          <input type="text" name="key_points[]" className="form-control" style={{ marginBottom: 8 }} required placeholder="Point 1  →  becomes a slide" />
          <input type="text" name="key_points[]" className="form-control" style={{ marginBottom: 8 }} placeholder="Point 2  (optional)" />
          <input type="text" name="key_points[]" className="form-control" style={{ marginBottom: 8 }} placeholder="Point 3  (optional)" />
          <input type="text" name="key_points[]" className="form-control" style={{ marginBottom: 8 }} placeholder="Point 4  (optional)" />
          <input type="text" name="key_points[]" className="form-control" placeholder="Point 5  (optional)" />
        </FormGroup>
        <FormGroup label="Call to action" required style={{ marginBottom: 0 }}>
          <input type="text" name="cta_text" className="form-control" required
            placeholder="e.g. Book now · DM us · Shop the link in bio" />
        </FormGroup>
      </FormSection>

      <FormSection title="🎯 Audience & Format">
        <FormGroup label="Target audience" required>
          <Chips name="audience" def="General"
            options={['Gen Z', 'Professionals', 'Parents', 'Business Owners', 'General']} />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Number of slides">
            <Chips name="num_slides" def="7" options={[['5', '5 slides'], ['7', '7 slides'], ['10', '10 slides']]} />
          </FormGroup>
          <FormGroup label="Visual style">
            <Chips name="visual_style" def="Bold Typography"
              options={['Bold Typography', 'Product Photo + Text', 'Minimal Editorial', 'Illustrated']} />
          </FormGroup>
        </div>
      </FormSection>

      <FormSection title="➕ Optional" sub="— leave blank and the pilot will craft everything">
        <div style={{ marginBottom: '0.75rem' }}>
          <UploadBox name="carousel_product_photos" accept="image/*" multiple icon="📦"
            label="Product / Reference Photos (Optional)"
            hint="Product shots or moodboard — anything visual that guides the pilot" />
        </div>
        <FormGroup label="Anything specific we should know?" style={{ marginBottom: 0 }}>
          <textarea name="special_notes" className="form-control" rows={2}
            placeholder="e.g. Must include our tagline 'Glow from within' · Avoid competitor names" />
        </FormGroup>
      </FormSection>

      <PriceCard amount="₹649" breakdown="Flat rate · 2 options per slide · ZIP (PNGs + caption.txt)"
        sla="Delivered within 2–3 hours of assignment" />
    </>
  );
}

// ── BRAND DEMO VIDEO ────────────────────────────────────────
export function BrandDemoVideoForm() {
  return (
    <>
      <FormSection title="📷 Upload Product / Brand Photos">
        <UploadBox name="product_photos" accept="image/*" multiple icon="📷"
          label="Upload Photos (min 5)" hint="Product shots, brand shots, lifestyle — any quality is fine" />
      </FormSection>
      <FormSection title="📹 Video Details">
        <div className="grid-2">
          <FormGroup label="Brand / Product Name" required>
            <input type="text" name="brand_name" className="form-control" placeholder="e.g. BRF Bottles" required />
          </FormGroup>
          <FormGroup label="Target Audience">
            <input type="text" name="target_audience" className="form-control" placeholder="e.g. Fitness enthusiasts 25–40" />
          </FormGroup>
        </div>
        <FormGroup label="Key Features / USPs (3–5 points)" required>
          <textarea name="usps" className="form-control" rows={2} required
            placeholder="e.g. Double-walled insulation, 1 litre, BPA-free, 10 colour options" />
        </FormGroup>
        <FormGroup label="Business URL(s)" required
          hint="The pilot will study these pages to extract your Brand DNA (tone, colors, audience, and palette) before building the video.">
          <textarea name="business_urls" className="form-control" rows={2} required
            placeholder="Paste any URL where your business is listed — website, Instagram, Facebook, LinkedIn, etc." />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Video Duration">
            <Chips name="duration" def="30s" options={[['15s', '15 sec'], ['30s', '30 sec'], ['60s', '60 sec']]} />
          </FormGroup>
          <FormGroup label="Tone">
            <Chips name="tone" def="Aspirational"
              options={[['Professional', 'Professional'], ['Fun', 'Fun'], ['Aspirational', 'Aspirational'], ['Urgent', 'Urgent / Offer']]} />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Target Platform">
            <Chips name="platform" def="Instagram Reel" options={['Instagram Reel', 'YouTube Shorts', 'Amazon', 'WhatsApp']} />
          </FormGroup>
          <FormGroup label="Music">
            <Chips name="music" def="energetic" options={[['soft', 'Soft'], ['energetic', 'Energetic'], ['none', 'None']]} />
          </FormGroup>
        </div>
        <FormGroup label="Brand Handle / Contact for End Frame" style={{ marginBottom: 0 }}>
          <input type="text" name="brand_contact" className="form-control" placeholder="e.g. @brfbottles or +91 98765 43210" />
        </FormGroup>
      </FormSection>
      <PriceCard amount="₹1,249" breakdown="Flat rate · video delivered in correct platform ratio"
        sla="Delivered within 3–5 hours of assignment" />
    </>
  );
}

// ── ANNOUNCEMENT PACK ───────────────────────────────────────
export function AnnouncementPackForm() {
  return (
    <>
      <FormSection title="📣 What Are You Announcing?">
        <div className="grid-2">
          <FormGroup label="Brand / Business Name" required>
            <input type="text" name="brand_name" className="form-control" placeholder="e.g. Brew & Co, Dr. Mehta's Clinic" required />
          </FormGroup>
          <FormGroup label="Announcement Type">
            <Chips name="announcement_type" def="Special Offer"
              options={['Special Offer', 'New Launch', 'Branch Opening', 'Event']} />
          </FormGroup>
        </div>
        <FormGroup label="Headline / Main Message" required
          hint="This is the big bold line on all 3 assets. Keep it short and punchy.">
          <input type="text" name="headline" className="form-control" required
            placeholder="e.g. 50% Off This Weekend Only · Now Open in Bandra · Launching: The Summer Menu" />
        </FormGroup>
        <FormGroup label="Supporting Details (2–3 points)">
          <textarea name="sub_points" className="form-control" rows={2}
            placeholder="e.g. Valid 15–17 Nov · All items included · No coupon needed" />
        </FormGroup>
        <FormGroup label="Business URL(s)" required
          hint="The pilot will study these pages to extract your Brand DNA (tone, colors, audience, and palette) before building the announcements.">
          <textarea name="business_urls" className="form-control" rows={2} required
            placeholder="Paste any URL where your business is listed — website, Instagram, Facebook, LinkedIn, etc." />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Call to Action" required>
            <input type="text" name="cta_text" className="form-control" placeholder="e.g. DM to book · Call now · Visit us today" required />
          </FormGroup>
          <FormGroup label="Contact (phone / handle / link)">
            <input type="text" name="contact" className="form-control" placeholder="e.g. +91 98765 43210 or @brewandco" />
          </FormGroup>
        </div>
        <FormGroup label="Tone" style={{ marginBottom: 0 }}>
          <Chips name="tone" def="Exciting" options={['Exciting', 'Premium', 'Friendly', 'Urgent']} />
        </FormGroup>
      </FormSection>
      <FormSection title="🎨 Brand & Visual">
        <FormGroup label="Brand Colours (hex or describe)">
          <input type="text" name="brand_colors" className="form-control" placeholder="e.g. #1A3A5C and gold · Navy + Cream · Orange and white" />
        </FormGroup>
        <FormGroup label="Visual Direction (optional)">
          <input type="text" name="visual_direction" className="form-control" placeholder="e.g. Dark moody background · Bright summer feel · Minimalist white with gold accents" />
        </FormGroup>
        <UploadBox name="logo_file" accept="image/*,.svg" icon="🖼️" label="Upload Logo (Optional)"
          hint="PNG with transparent background preferred" />
        <div style={{ marginTop: '0.75rem' }}>
          <UploadBox name="reference_image" accept="image/*" icon="📸" label="Reference Image (Optional)"
            hint="A photo of your product, store, or dish to use as the hero visual" />
        </div>
      </FormSection>
      <PriceCard amount="₹499" breakdown="Flat rate · Instagram Post + Story + WhatsApp card"
        sla="Delivered within 2–3 hours of assignment" />
    </>
  );
}
