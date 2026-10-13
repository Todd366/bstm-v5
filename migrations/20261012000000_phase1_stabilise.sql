-- Migration: phase1_stabilise
--
-- Additive and safe to re-run. Touches only the `activation` schema.
--
-- 1. People share names. youth.name was UNIQUE (case-insensitive), so a
--    second "Thabo Mokoena" could never register. Identity is email.
-- 2. Businesses are identified by name + location, not name alone.
-- 3. Seed the capability catalog (it held a single row, so matching
--    returned nothing for every new youth). Categories equal the
--    interest choices in the registration questionnaire.
-- 4. Indexes for the queries the new self-service flows run.

DROP INDEX IF EXISTS activation.youth_name_ci_unique;

DROP INDEX IF EXISTS activation.businesses_name_ci_unique;

CREATE UNIQUE INDEX IF NOT EXISTS businesses_name_location_ci_unique
    ON activation.businesses (lower(name), lower(location));

INSERT INTO activation.capabilities (name, category, description) VALUES
    -- Technology
    ('Web Development',        'Technology', 'Build and maintain websites'),
    ('Mobile Apps',            'Technology', 'Build phone apps and progressive web apps'),
    ('Data Entry',             'Technology', 'Capture and clean records accurately'),
    ('Computer Repair',        'Technology', 'Fix computers, phones and networks'),
    ('Chatbots',               'Technology', 'Build WhatsApp or Telegram bots'),
    ('Spreadsheets',           'Technology', 'Excel / Sheets models and reports'),
    -- Business
    ('Customer Service',       'Business', 'Serve and follow up customers'),
    ('Sales',                  'Business', 'Find and close customers'),
    ('Admin Support',          'Business', 'Office administration and scheduling'),
    ('Project Coordination',   'Business', 'Plan and track small projects'),
    ('Procurement',            'Business', 'Source and buy supplies'),
    -- Creative
    ('Graphic Design',         'Creative', 'Logos, flyers and brand kits'),
    ('Photography',            'Creative', 'Product and event photos'),
    ('Video Editing',          'Creative', 'Edit short videos and promos'),
    ('Social Media',           'Creative', 'Run a business''s social pages'),
    ('Copywriting',            'Creative', 'Write adverts and web content'),
    ('Music Production',       'Creative', 'Record and produce music'),
    -- Agriculture
    ('Crop Farming',           'Agriculture', 'Grow vegetables and field crops'),
    ('Poultry',                'Agriculture', 'Raise and sell poultry'),
    ('Livestock',              'Agriculture', 'Cattle, goats and small stock'),
    ('Irrigation',             'Agriculture', 'Set up and maintain water systems'),
    ('Urban Farming',          'Agriculture', 'Small-space and tunnel farming'),
    -- Trades
    ('Carpentry',              'Trades', 'Furniture and building woodwork'),
    ('Plumbing',               'Trades', 'Install and repair water systems'),
    ('Electrical',             'Trades', 'Wiring and solar installation'),
    ('Welding',                'Trades', 'Metal fabrication and repairs'),
    ('Tailoring',              'Trades', 'Sewing and clothing alterations'),
    ('Driving',                'Trades', 'Deliveries and passenger transport'),
    ('Painting',               'Trades', 'Building and sign painting'),
    -- Finance
    ('Bookkeeping',            'Finance', 'Record income and expenses'),
    ('Accounting',             'Finance', 'Financial statements and tax records'),
    ('Budgeting',              'Finance', 'Plan and track business budgets'),
    ('Payments',               'Finance', 'Mobile money and card payments'),
    -- Research
    ('Field Research',         'Research', 'Interviews and on-site observation'),
    ('Surveys',                'Research', 'Design and run surveys'),
    ('Data Analysis',          'Research', 'Turn data into findings'),
    ('Report Writing',         'Research', 'Write clear reports'),
    -- Community
    ('Event Coordination',     'Community', 'Plan and run community events'),
    ('Teaching',               'Community', 'Tutor and run workshops'),
    ('Community Outreach',     'Community', 'Reach and organise people'),
    ('Translation',            'Community', 'English and Setswana translation')
ON CONFLICT (name) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_assignments_opportunity_status
    ON activation.opportunity_assignments (opportunity_id, status);

CREATE INDEX IF NOT EXISTS idx_opportunities_status
    ON activation.opportunities (status);

CREATE INDEX IF NOT EXISTS idx_evidence_trial
    ON activation.evidence (trial_id);

CREATE INDEX IF NOT EXISTS idx_activity_actor
    ON activation.activity (actor_id, created_at DESC);
