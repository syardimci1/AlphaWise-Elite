-- İki sahte kullanıcı + üçüncü bir "yetim" kullanıcı (fail-closed testi için)
INSERT INTO auth.users (id, email) VALUES
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'a@test.local'),
  ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'b@test.local'),
  ('cccccccc-cccc-4ccc-8ccc-cccccccccccc', 'c@test.local');

-- 005'teki tetik profilleri OTOMATIK olusturmus olmali; dogrula
SELECT 'tetikle_olusan_profil' AS kontrol, COUNT(*)::text FROM public.profiles;

-- portföyler
INSERT INTO public.user_portfolios (user_id, portfolio_name, tickers) VALUES
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'A-Portfoy', ARRAY['AAPL','MSFT']),
  ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'B-Portfoy', ARRAY['NVDA','TSLA']),
  ('cccccccc-cccc-4ccc-8ccc-cccccccccccc', 'C-Yetim',   ARRAY['GOOGL']);

SELECT 'profil' AS tablo, COUNT(*)::text FROM public.profiles
UNION ALL SELECT 'portfoy', COUNT(*)::text FROM public.user_portfolios;
