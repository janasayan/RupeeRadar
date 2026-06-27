# RupeeRadar — Project Context

## Overview

**RupeeRadar** is an AI-powered personal finance assistant built for an AI Challenge. It helps working professionals understand where their money is going by analyzing bank statement data and turning raw transactions into clear, actionable insights.

## Background

Working professionals often make hundreds of monthly transactions across:

- UPI
- Cards
- Bank transfers
- Subscriptions
- EMIs
- Rent
- Shopping
- Food delivery
- Travel
- Investments

Bank statements contain all of this information, but transaction descriptions are messy, inconsistent, and difficult to categorize manually.

## Problem

Users need a way to upload bank statement data and automatically:

- Extract and clean transactions
- Categorize expenses
- Detect recurring payments
- Generate spending insights
- View results in a simple dashboard or report

## Objective

Build an end-to-end solution that converts raw financial transaction data into meaningful personal finance insights, and proactively guides users toward better saving habits.

The application should help users answer:

- What are my biggest spending categories?
- How much did I spend this month?
- Which transactions are recurring subscriptions or EMIs?
- What was my biggest transaction?
- What are the top insights from my spending behavior?
- Am I overspending on wants relative to my income?
- Where exactly can I cut back to save more?

## Core Requirements

1. **Input** — Accept bank statement data as input.
2. **Extraction & cleaning** — Extract or clean transactions into a structured format.
3. **Categorization** — Categorize transactions into meaningful groups:
   - Food
   - Travel
   - Shopping
   - Bills
   - EMI
   - Subscriptions
   - Salary
   - Rent
   - Investments
   - Other
4. **Recurring detection** — Identify recurring transactions such as subscriptions, EMIs, rent, SIPs, or insurance payments.
5. **Metrics** — Calculate key financial metrics:
   - Total income
   - Total spend
   - Savings
   - Top categories
   - Biggest transactions
6. **Insights** — Generate clear, human-readable spending insights using actual transaction amounts.
7. **Needs vs Wants classification** — Classify every spending category as a *need* or a *want*:
   - **Needs** (non-negotiable): Rent, EMI, Bills, Investments, Salary (income)
   - **Wants** (discretionary): Food (dining/delivery portion), Shopping, Travel (non-commute), Subscriptions, Other
   - Mixed categories (e.g. Food covers groceries = need and Swiggy = want) are handled by sub-category hints or LLM classification.
8. **Savings recommendations** — When the user's *wants* spending exceeds a threshold derived from their declared or inferred monthly income:
   - Default threshold: wants > 30% of net income triggers recommendations.
   - Each over-budget want category surfaces specific, actionable suggestions (e.g. "Reduce food delivery by ₹X/month to meet your 30% wants budget").
   - Suggestions are ranked by potential savings impact (highest first).
   - Needs are never penalized; the system only recommends reducing wants.
9. **Presentation** — Present the final output through a simple user interface, dashboard, or downloadable report including a dedicated *Savings Recommendations* panel.

## Expected Output (Prototype)

The working prototype must demonstrate:

- Cleaned transaction data
- Categorized expenses with needs/wants labels
- Recurring payment detection
- Spend summary dashboard
- At least three personalized financial insights
- A *Savings Recommendations* panel with ranked, actionable suggestions for over-budget wants categories
- A final report or visual summary that can be shared

## Evaluation Criteria

Submissions are evaluated on:

- Accuracy of transaction cleaning and categorization
- Quality of financial insights
- Ability to handle real-world messy transaction descriptions
- Simplicity and usefulness of the user experience
- Completeness of the end-to-end workflow
- Privacy-conscious handling of sensitive financial data

## Constraints

- Prioritize a **working end-to-end prototype** over perfect support for every bank format.
- Technology stack and implementation approach are flexible.
- Handle sensitive financial data with privacy in mind.

## Final Deliverable

A deployed or locally runnable application that:

1. Takes raw bank statement data as input
2. Produces a clear personal finance summary showing where the user's money is going

## Source

Derived from [`docs/problemStatement.txt`](docs/problemStatement.txt).
