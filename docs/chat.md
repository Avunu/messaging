# Messaging Chat Interface

A modern, chat-like messaging interface for Frappe Communications, powered by [vue-advanced-chat](https://github.com/advanced-chat/vue-advanced-chat).

## Features

- **Unified Inbox**: View all Email and SMS communications in one chat-like interface
- **Real-time Updates**: Messages update in real-time using Frappe's realtime system
- **Dark Mode Support**: Automatically adapts to Frappe's theme settings
- **Contact Integration**: Links to Frappe Contact records for quick access
- **Reference Documents**: View and link to related Frappe documents
- **File Attachments**: Send and receive file attachments
- **Search**: Search across all conversations
- **Medium Filter**: Filter by Email, SMS, or all messages

## Architecture

### Backend (Python)

The backend API is located in `messaging/messaging/api/chat/`:

- **`types.py`**: TypedDict definitions matching vue-advanced-chat structures
- **`api.py`**: Whitelist API endpoints using Frappe Query Builder
  - `get_rooms()`: Get conversation threads (grouped by sender/recipient)
  - `get_messages()`: Get messages for a specific conversation
  - `send_message()`: Send email or SMS messages
  - `mark_messages_seen()`: Mark messages as read
  - `get_current_user()`: Get current user info for chat
  - `search_rooms()`: Search conversations
  - `get_unread_count()`: Get total unread message count

### Frontend (TypeScript/Vue)

The frontend is located in `messaging/public/js/chat/`:

- **`types.ts`**: TypeScript interfaces for vue-advanced-chat and Frappe
- **`api.ts`**: Typed API client for backend calls
- **`useChat.ts`**: Vue composable for state management
- **`ChatView.vue`**: Main chat component using vue-advanced-chat
- **`chat.bundle.ts`**: Frappe view integration

## Installation

The chat interface is included with the messaging app. After installing:

```bash
cd frappe-bench
bench --site yoursite install-app messaging
bench build --app messaging
bench migrate
```

## Usage

1. Navigate to **Communication** in Frappe desk
2. The default view is now the Chat interface
3. Use the medium filter to show Email, SMS, or all messages
4. Click a conversation to view and reply to messages
5. Use the "New Message" button to start a new conversation

## Configuration

No additional configuration is required. The chat interface uses existing Frappe Communication and SMS settings.

## API Reference

### get_rooms

```python
get_rooms(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    medium: str = "All"
) -> RoomsResponse
```

### get_messages

```python
get_messages(
    room_id: str,
    page: int = 1,
    limit: int = 50,
    before_id: str = ""
) -> MessagesResponse
```

### send_message

```python
send_message(
    room_id: str,
    content: str,
    files: list[dict] | None = None,
    reply_message_id: str = "",
    subject: str = ""
) -> SendMessageResponse
```

## Room ID Format

Room IDs follow the pattern: `{medium}:{identifier}[:ref_dt:ref_name]`

Examples:
- `SMS:+15551234567` - SMS conversation with a phone number
- `Email:user@example.com` - Email thread with an email address
- `Email:user@example.com:Lead:LEAD-00001` - Email linked to a Lead

## Type Definitions

See `messaging/messaging/api/chat/types.py` for Python types and `messaging/public/js/chat/types.ts` for TypeScript interfaces.

## Development

### Building

```bash
cd frappe-bench/apps/messaging
yarn install
bench build --app messaging
```

### Type Checking

```bash
yarn typecheck
```

### Watch Mode

```bash
yarn watch
```

## Contributing

Contributions are welcome! Please ensure:

1. Python code uses type annotations
2. TypeScript code is properly typed
3. Use Frappe Query Builder for all database operations
4. Follow vue-advanced-chat patterns for frontend components
