// Wizard forms — SMB Visual Content: Instagram Carousel, Brand Demo Video,
// Announcement Pack.
import { useRef } from 'react';
import { FormSection, FormGroup, Chips, UploadBox, PriceCard } from './widgets.jsx';

// ── INSTAGRAM CAROUSEL ──────────────────────────────────────
const IDEA_SUGGESTIONS = [
  ['Service Feature', 'Describe a key service feature and why it matters to our audience'],
  ['Product Feature', 'Highlight a product feature with visuals for each benefit'],
  ['Product Offer', 'Announce a limited-time product offer or discount with urgency'],
  ['Product Launch', 'Launch a new product — build curiosity then reveal'],
  ['Sale', 'Announce a sale with compelling visuals and clear savings'],
  ['Product in Use', 'Show the product being used naturally in different real-life environments'],
  ['Brand Story', 'Tell our brand story — how we started, what we stand for, where we are going'],
  ['How-To Tutorial', 'Walk the audience through a step-by-step tutorial or how-to guide'],
];

export function InstagramCarouselForm() {
  const ideaRef = useRef(null);
  return (
    <>
      <FormSection title="🏷 Brand Basics">
        <div className="grid-2">
          <FormGroup label="Brand / Business Name" required>
            <input type="text" name="brand_name" className="form-control" placeholder="e.g. GlowUp Skincare" required />
          </FormGroup>
          <FormGroup label="Industry / Niche" required>
            <input type="text" name="industry_niche" className="form-control" placeholder="e.g. Clean Beauty, Real Estate, SaaS, Food & Beverage" required />
          </FormGroup>
        </div>
        <FormGroup label="Business URL(s)" required style={{ marginBottom: 0 }}
          hint="The pilot will study these pages to understand your brand before building the carousel.">
          <textarea name="business_urls" className="form-control" rows={2} required
            placeholder="Paste any URL where your business is listed — website, Instagram, Facebook, LinkedIn, JustDial, TradeIndia, etc." />
        </FormGroup>
      </FormSection>

      <FormSection title="💡 Carousel Brief">
        <FormGroup label="Carousel Idea / Story" required>
          <textarea ref={ideaRef} name="carousel_idea" className="form-control" rows={3} required
            placeholder="Describe what story or idea you want this carousel to tell. e.g. Show how our new moisturiser works step-by-step · Launch our new summer collection with 5 product highlights · Explain 3 reasons our service saves time" />
          <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: 6 }}>Quick picks — click to fill:</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
            {IDEA_SUGGESTIONS.map(([label, text]) => (
              <button key={label} type="button" className="chip-suggest-btn"
                onClick={() => { if (ideaRef.current) ideaRef.current.value = text; }}>{label}</button>
            ))}
          </div>
        </FormGroup>
        <FormGroup label="Carousel Style" required>
          <Chips name="carousel_style" def="Text Based"
            options={['Text Based', 'Image Based', 'Infographics', 'Data Based', 'Realistic', 'Comical', 'Futuristic', 'Bold Typography', 'Minimal', 'Tutorial / How-To']} />
        </FormGroup>
        <FormGroup label="Number of Slides" style={{ marginBottom: 0 }}>
          <Chips name="num_slides" def="5" options={[['5', '5 slides'], ['6', '6 slides'], ['8', '8 slides'], ['10', '10 slides']]} />
        </FormGroup>
      </FormSection>

      <FormSection title="🎯 Campaign Brief">
        <div className="grid-2">
          <FormGroup label="Product / Service Being Promoted" required>
            <input type="text" name="product_service" className="form-control" placeholder="e.g. Vitamin C Serum, Email Marketing Package, Coaching Programme" required />
          </FormGroup>
          <FormGroup label="Unique Selling Point (USP)">
            <input type="text" name="usp" className="form-control" placeholder="e.g. No harsh chemicals, results in 7 days" />
          </FormGroup>
        </div>
        <div className="grid-2">
          <FormGroup label="Target Audience" required>
            <input type="text" name="target_audience" className="form-control" placeholder="e.g. Women 22–40 into clean beauty, SMB founders in India" required />
          </FormGroup>
          <FormGroup label="Audience Pain Point">
            <input type="text" name="pain_point" className="form-control" placeholder="e.g. Dull, uneven skin tone · Can't get clients online" />
          </FormGroup>
        </div>
        <FormGroup label="Goal of This Carousel" required>
          <Chips name="goal" def="Drive Sales"
            options={[['Drive Sales', 'Drive Sales'], ['Build Awareness', 'Build Awareness'], ['Get Leads', 'Get Leads'], ['Grow Following', 'Grow Following'], ['Educate Audience', 'Educate']]} />
        </FormGroup>
        <FormGroup label="Key Message" required hint="The single message you want this carousel to leave with the reader">
          <input type="text" name="key_message" className="form-control" placeholder="e.g. Brighter skin in 7 days — naturally · 3 steps to close more clients" required />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Offer / CTA" required>
            <input type="text" name="cta_text" className="form-control" placeholder="e.g. 20% off first order — link in bio · Book a free call today" required />
          </FormGroup>
          <FormGroup label="CTA Button Text (max 4 words)">
            <input type="text" name="cta_button_text" className="form-control" placeholder="e.g. Shop Now · Book Free Call · Grab the Deal" />
          </FormGroup>
        </div>
        <FormGroup label="Stage of Awareness"
          hint="Cold → leads with the problem · Warm → leads with the solution · Existing → leads with results">
          <Chips name="audience_stage" def="Cold"
            options={[['Cold', 'Cold Audience'], ['Warm', 'Warm Followers'], ['Existing', 'Existing Customers']]} />
        </FormGroup>
      </FormSection>

      <FormSection title="🎨 Visual Identity">
        <div className="grid-2">
          <FormGroup label="Brand Personality">
            <input type="text" name="brand_personality" className="form-control" placeholder="e.g. Fresh, confident, approachable · Bold, premium, no-nonsense" />
          </FormGroup>
          <FormGroup label="Color Preference">
            <input type="text" name="brand_colors" className="form-control" placeholder="e.g. Soft peach, cream, gold · Navy + white + lime green" />
          </FormGroup>
        </div>
        <FormGroup label="Emotion to Evoke">
          <Chips name="emotion_to_evoke" def="Confidence"
            options={['Confidence', 'Trust', 'Excitement', 'FOMO', 'Aspiration', 'Calm / Comfort']} />
        </FormGroup>
        <FormGroup label="Visual Style">
          <Chips name="visual_style" def="Product Flat Lay + Bold Typography"
            options={[['Product Flat Lay + Bold Typography', 'Product Flat Lay'], ['Lifestyle Photography + Soft Text', 'Lifestyle Photo'], ['Bold Graphic + Minimal Image', 'Bold Graphic'], ['Tutorial / Step-by-Step Illustration', 'Tutorial Steps'], ['Before / After Reveal', 'Before / After'], ['Minimal Clean + Icon-Led', 'Minimal + Icons']]} />
        </FormGroup>
        <div className="grid-2">
          <FormGroup label="Font Style">
            <Chips name="font_style" def="Modern Sans" options={['Modern Sans', 'Classic Serif', 'Playful', 'Bold Display']} />
          </FormGroup>
          <FormGroup label="Aspect Ratio">
            <Chips name="aspect_ratio" def="4:5 Portrait" options={['4:5 Portrait', '1:1 Square']} />
          </FormGroup>
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <UploadBox name="logo_file" accept="image/*,.svg" icon="🖼️" label="Upload Logo (Optional)"
            hint="PNG with transparent background preferred" />
        </div>
        <UploadBox name="carousel_product_photos" accept="image/*" multiple icon="📦"
          label="Product / Reference Photos (Optional)"
          hint="Product shots, reference images, moodboard — anything visual that guides the pilot" />
      </FormSection>

      <FormSection title="✍️ Caption Direction" sub="— Optional. Leave blank and the pilot will craft everything.">
        <FormGroup label="Headline Direction (max 8 words)">
          <input type="text" name="headline_direction" className="form-control" placeholder="e.g. Stop losing clients after the first call" />
        </FormGroup>
        <FormGroup label="Hashtag Seeds (any specific hashtags to include)" style={{ marginBottom: 0 }}>
          <textarea name="hashtag_seeds" className="form-control" rows={2} placeholder="e.g. #cleanbeauty #glowupskincare #vitaminc" />
        </FormGroup>
      </FormSection>

      <FormSection title="📋 Additional Notes" sub="(optional)">
        <FormGroup label="Anything else the pilot should know?" style={{ marginBottom: 0 }}>
          <textarea name="key_points" className="form-control" rows={3}
            placeholder="e.g. Avoid competitor brand names · Keep it minimal · Must include our tagline 'Glow from within'" />
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
