-- Populate publicly_traded + ticker_symbol for sponsors, bridging to Project 2
-- (Biopharma Earnings Surprise Tracker).
--
-- Acquired/subsidiary sponsors are mapped to their CURRENT public parent's
-- ticker, since that's whose earnings actually get reported.
-- IMPORTANT: Boehringer Ingelheim, Chiesi Farmaceutici, and Zambon SpA are
-- large but PRIVATELY/family-owned -- intentionally left as not publicly traded.
--
-- This is not exhaustive -- it covers confidently-identified major/mid-cap
-- public companies and known subsidiaries. Smaller sponsors default to FALSE,
-- which is honestly correct for most (private biotechs, academic institutions,
-- hospital systems, government bodies).

-- Directly publicly traded companies
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'ABBV' WHERE sponsor_name = 'AbbVie';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'AMGN' WHERE sponsor_name = 'Amgen';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'ARWR' WHERE sponsor_name = 'Arrowhead Pharmaceuticals';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'AZN' WHERE sponsor_name = 'AstraZeneca';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'BIIB' WHERE sponsor_name = 'Biogen';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'BMY' WHERE sponsor_name = 'Bristol-Myers Squibb';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'CPIX' WHERE sponsor_name = 'Cumberland Pharmaceuticals';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'GILD' WHERE sponsor_name = 'Gilead Sciences';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'GSK' WHERE sponsor_name = 'GlaxoSmithKline';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'MNKD' WHERE sponsor_name = 'Mannkind Corporation';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'MNOV' WHERE sponsor_name = 'MediciNova';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'NVS' WHERE sponsor_name = 'Novartis Pharmaceuticals';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'PLRX' WHERE sponsor_name = 'Pliant Therapeutics, Inc.';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'PRTC' WHERE sponsor_name = 'PureTech';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'REDX' WHERE sponsor_name = 'Redx Pharma Ltd';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'SNY' WHERE sponsor_name = 'Sanofi';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'SNDX' WHERE sponsor_name = 'Syndax Pharmaceuticals';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'TBPH' WHERE sponsor_name = 'Theravance Biopharma';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'TRVI' WHERE sponsor_name = 'Trevi Therapeutics';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'UTHR' WHERE sponsor_name = 'United Therapeutics';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'UTHR' WHERE sponsor_name = 'Lung Biotechnology PBC'; -- wholly owned by United Therapeutics
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'VICO.ST' WHERE sponsor_name = 'Vicore Pharma AB';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'RHHBY' WHERE sponsor_name = 'Hoffmann-La Roche';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = '3402.T' WHERE sponsor_name = 'Toray Industries, Inc';

-- Acquired subsidiaries -> mapped to current public parent's ticker
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'JNJ' WHERE sponsor_name = 'Actelion';                -- acquired by J&J, 2017
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'JNJ' WHERE sponsor_name = 'Centocor, Inc.';          -- J&J subsidiary
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'RHHBY' WHERE sponsor_name = 'Genentech, Inc.';       -- Roche subsidiary
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'RHHBY' WHERE sponsor_name = 'InterMune';             -- acquired by Roche, 2014
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'BMY' WHERE sponsor_name = 'Celgene';                 -- acquired by BMS, 2019
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'SNY' WHERE sponsor_name = 'Kadmon Corporation, LLC'; -- acquired by Sanofi, 2021
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'SNY' WHERE sponsor_name = 'Genzyme, a Sanofi Company';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'AZN' WHERE sponsor_name = 'MedImmune LLC';           -- AstraZeneca subsidiary
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'PFE' WHERE sponsor_name LIKE 'Wyeth is now%';        -- now Pfizer subsidiary
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'PFE' WHERE sponsor_name = 'Global Blood Therapeutics'; -- acquired by Pfizer, 2022
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = 'MRK' WHERE sponsor_name LIKE 'Afferent Pharmaceuticals%'; -- Merck subsidiary

-- International public parents (Asia-listed)
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = '069620.KS' WHERE sponsor_name = 'Daewoong Pharmaceutical Co. LTD.';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = '000210.KS' WHERE sponsor_name = 'IlDong Pharmaceutical Co Ltd';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = '002653.SZ' WHERE sponsor_name = 'Haisco Pharmaceutical Group Co., Ltd.';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = '600276.SS' WHERE sponsor_name = 'Guangdong Hengrui Pharmaceutical Co., Ltd'; -- Hengrui Pharma parent
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = '6988.T' WHERE sponsor_name = 'Nitto Denko Corporation';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = '688062.SS' WHERE sponsor_name = 'Mabwell (Shanghai) Bioscience Co., Ltd.';
UPDATE sponsors SET publicly_traded = TRUE, ticker_symbol = '288330.KQ' WHERE sponsor_name = 'Bridge Biotherapeutics, Inc.';

-- Verification query -- run after the updates
SELECT sponsor_name, publicly_traded, ticker_symbol
FROM sponsors
WHERE publicly_traded = TRUE
ORDER BY sponsor_name;