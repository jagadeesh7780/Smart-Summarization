# Vercel Deployment Guide

## Required Environment Variables
Set these in Vercel Dashboard → Project → Settings → Environment Variables:

| Variable | Value |
|---|---|
| `SECRET_KEY` | any long random string e.g. `supersecretkey123abc` |
| `GROQ_API_KEY` | your Groq API key from https://console.groq.com/keys |
| `GEMINI_API_KEY` | (optional) from https://makersuite.google.com/app/apikey |
| `VERCEL` | `1` |

## Steps to Deploy
1. Push this code to GitHub
2. Go to https://vercel.com → New Project → Import your GitHub repo
3. Set Framework Preset to **Other**
4. Add all environment variables above
5. Deploy

## Notes
- SQLite DB is stored in `/tmp` on Vercel (resets between cold starts — use a persistent DB like PlanetScale/Supabase for production)
- Uploaded files are stored in `/tmp` (ephemeral)
- pytesseract (OCR) won't work on Vercel free tier (no system binaries)
