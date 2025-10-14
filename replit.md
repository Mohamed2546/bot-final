# Telegram Bot - Account Management System

## Overview
This project is a Telegram bot designed to automate the collection, verification, and management of user-submitted Telegram accounts. It leverages Telethon for session creation and review, provides a reward system for users, and offers a comprehensive admin control panel. The bot's core purpose is to automate account management, including spam/ban checks, user balances, and withdrawals, with multi-language support (primarily Arabic).

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Fixes (October 2025)
### Critical Issues Fixed:
1. **Connected Missing Handlers**: Added 3 essential handler modules that were disconnected:
   - `admin_handlers_extra.py` - User search, balance control, ban/unban, broadcast messages
   - `admin_countries.py` - Country management, withdrawals history
   - `admin_accounts.py` - Account viewing, session export, import history

2. **Security Improvements**: 
   - Moved hardcoded secrets to environment variables (2FA password, API credentials)
   - Created centralized config for `TWO_FA_PASSWORD`, `TELETHON_API_ID`, `TELETHON_API_HASH`
   - All sensitive data now loaded from environment or config with safe defaults

3. **Fixed Infinite Recursion**: 
   - Replaced unbounded recursion in `main.py` and `review_system.py` with retry counters
   - Added max retries (5 for review system, 3 for internal loops)
   - Implemented exponential backoff for failures

4. **Unified Dependencies**: 
   - Resolved conflict between `requirements.txt` (telethon==1.28.5) and `pyproject.toml` (telethon>=1.41.2)
   - Removed erroneous `telegram>=0.0.1` package
   - Standardized to telethon>=1.41.2

5. **LSP Error Fixes**:
   - Fixed unbound variable errors (ReviewSystem, AccountMonitor, admin_commands)
   - Added null checks before using imported classes
   - Resolved all critical main.py errors (0 errors now)
   - Improved type safety with explicit None initialization

6. **Async Notification System Fix**:
   - Fixed RuntimeError in review notifications by using `asyncio.run_coroutine_threadsafe`
   - Review system now captures event loop reference (`self.loop`) on startup
   - All notifications (delay/approval/rejection) now properly dispatch from sync methods to async event loop
   - Prevents silent notification failures when called from review thread

## System Architecture

### UI/UX Decisions
The bot utilizes multi-level inline keyboards for intuitive navigation, especially within the comprehensive admin control panel, which is designed with an Arabic interface to cater to its target user base. User onboarding includes channel subscription verification and captcha validation.

### Technical Implementations
1.  **Database Architecture**: Uses SQLite3 for simplicity and portability, with a normalized schema across tables like `users`, `accounts`, `countries`, `account_reviews`, `rate_limits`, `withdrawals`, and `monitor_logs` to ensure data integrity and flexible querying.
2.  **Bot Framework**: Built with `python-telegram-bot v20.7` using a modular, handler-based architecture for distinct functionalities (e.g., `start_handler`, `admin_panel`).
3.  **Session Management**: Employs Telethon with `StringSession` to store encrypted sessions in the database, incorporating dynamic device and version spoofing (Android, iOS profiles) for anti-detection and persistence during the review process.
4.  **Review System**: An asynchronous loop in `review_system.py` automates account verification by checking SpamBot status, validating sessions, and updating account statuses, including robust error handling for Telegram API rate limits and banned numbers.
5.  **Account Monitoring System**: A periodic account health check system in `account_monitor.py` with configurable interval (1-24 hours, default: 2 hours) to verify all approved accounts remain valid and active. It checks session validity and frozen status, automatically updating account status when issues are detected. Logs all monitoring activities to the `monitor_logs` table. Includes admin controls to enable/disable monitoring and adjust check intervals.
6.  **Rate Limiting**: A database-backed sliding window rate limiter prevents abuse by tracking user actions and attempts per configurable time windows.
7.  **Admin Control Panel**: A multi-level inline keyboard navigation system provides real-time statistics, user and balance management, broadcast messaging, country configuration, withdrawal approval workflows, and bot state control.
8.  **User Flow**: Manages a multi-step onboarding process (channel verification, captcha, phone/code submission, 2FA) with database flags for state management. Enhanced with:
    *   **Phone Number Duplicate Prevention**: Implemented `check_phone_number_status()` to prevent adding duplicate numbers - approved and pending numbers cannot be added again, rejected numbers require 24-hour waiting period before re-submission.
    *   **Streamlined UX**: After captcha validation, users see the main menu immediately (same as /start flow), allowing them to choose "Add Account" and submit their phone number directly.
    *   **Automatic Country Validation**: Phone numbers are automatically validated against active countries (is_active = TRUE) by checking the phone number prefix against available country codes - no manual country selection required.
9.  **Configuration Management**: Centralized settings in `config.py` (bot tokens, API credentials, rate limits) support environment-based configuration.
10. **Logging**: Dual-handler logging (file and console) with configurable levels aids in debugging and monitoring.
11. **Country Management System**: Enables per-country pricing, capacity limits, flag display, and review time customization, dynamically configured via the database.
12. **Advanced Admin Panel**: A comprehensive, multi-module admin system with Arabic UI, including:
    *   Statistics Dashboard: Total users, account metrics, withdrawals, active proxies.
    *   Settings Control: Toggle bot operations, configure checks, edit messages.
    *   User Management: Search, balance control, ban/unban, export sessions.
    *   Country Management: CRUD operations for countries, capacity adjustments.
    *   Account Management: View accounts, import ZIP/JSON sessions, track import history.
    *   Messaging System: Broadcast and individual messages.
    *   Bot Control: Manage secondary admins, proxies, system diagnostics.
    *   Withdrawal Management: Review, approve, or reject withdrawal requests.
    *   Ready Accounts Sales System: Allows users to purchase pre-verified accounts, with associated admin controls for pricing, sales statistics, and purchase history. This includes secure purchase flows, login code retrieval, and account logout functionality.

### Feature Specifications
*   Automated Telegram account collection and verification.
*   User balance and withdrawal management.
*   Multi-language support (Arabic).
*   Comprehensive admin panel for full bot control.
*   Dynamic device and version spoofing for Telethon sessions.
*   Automated SpamBot checks for account status.
*   Periodic health monitoring for all approved accounts (every 2 hours).
*   Rate limiting to prevent system abuse.
*   User onboarding with channel verification and captcha.
*   Country-specific pricing and capacity management for accounts.
*   Export of approved sessions in ZIP/JSON formats.
*   Ready Accounts Sales System for users to buy pre-verified accounts.

## External Dependencies

### Third-Party Libraries
*   **python-telegram-bot (v20.7)**: Telegram Bot API wrapper.
*   **Telethon (v1.28.5)**: Telegram Client API for user account operations.

### External Services
*   **Telegram Bot API**: For bot interactions and messaging.
*   **Telegram Client API (MTProto)**: For user session creation and management.
*   **@SpamBot**: For official Telegram spam status verification.

### Environment Variables
*   `BOT_TOKEN`: Telegram bot token.
*   `ADMIN_ID`: Primary administrator user ID.
*   `API_ID`: Telegram API application ID.
*   `API_HASH`: Telegram API application hash.

### Storage
*   **SQLite Database**: `bot.db` for all persistent data.
*   **Log Files**: `bot.log` for system monitoring.

### Integrations
*   **Channel Subscription**: Mandatory check to a configured Telegram channel (`CHANNEL_USERNAME`) during user onboarding.