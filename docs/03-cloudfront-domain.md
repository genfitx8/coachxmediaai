# 03 — CloudFront & Custom Domain Setup

This document explains how to configure CloudFront and a custom domain for the CoachX Media AI platform.

---

## Frontend on Vercel (recommended for Next.js)

The simplest option is to deploy the Next.js frontend to **Vercel**:

1. Connect the GitHub repository to Vercel.
2. Set the root directory to `frontend`.
3. Add the environment variable `NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com/api/v1`.
4. Configure your custom domain in Vercel's project settings.

---

## Frontend via S3 + CloudFront (static export)

If you prefer full AWS hosting:

1. Build a static export:
   ```bash
   cd frontend
   npm run build
   ```
2. Upload the `out/` directory to an S3 bucket configured for static website hosting.
3. Create a CloudFront distribution pointing to the S3 bucket.
4. Add a CNAME record pointing `www.yourdomain.com` to the CloudFront domain.

---

## API Behind CloudFront

To serve the API through CloudFront:

1. Create a CloudFront distribution with two origins:
   - `api.yourdomain.com` → ALB (for `/api/*` paths)
   - S3 or Vercel origin (for `/*`)
2. Set the `Cache-Control` header appropriately for API responses (`no-store`).
3. Forward the `Authorization` header to the ALB origin.

---

## TLS / ACM

Request a certificate in ACM (us-east-1 for CloudFront):

```bash
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names "*.yourdomain.com" \
  --validation-method DNS \
  --region us-east-1
```

Validate using the DNS records provided and attach the certificate to CloudFront.
