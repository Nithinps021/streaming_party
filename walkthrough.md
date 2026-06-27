# StreamParty Walkthrough

The StreamParty real-time movie-watching application has been successfully built and deployed locally!

## Accomplishments

1. **Monorepo Setup**: Configured a `streamparty` directory containing both `frontend` and `backend`.
2. **Backend Architecture**:
   - Built with **Python + FastAPI**.
   - Used **fakeredis** to simulate Redis as requested ("use redis to store the value in memory"), allowing the app to run completely in-memory without requiring you to install a separate Redis server!
   - Implemented `POST /api/room` to generate expiring room IDs and Admin tokens.
   - Built a robust WebSocket endpoint `/ws/{room_id}` that handles secure real-time broadcasting.
3. **Frontend Architecture**:
   - Built with **Vue 3 + Vite**.
   - Styled with a premium **Vanilla CSS** design system featuring dark mode, glassmorphism, and responsive layouts.
   - Setup **Vite PWA plugin** for offline capabilities.
4. **Real-time Sync**:
   - Strict synchronization logic in `VideoPlayer.vue` where the Admin controls the play, pause, and seek actions, instantly updating all connected peers.
5. **Live Chat**:
   - Integrated a sleek, auto-scrolling live chat component in `ChatSidebar.vue` that connects directly to the room's WebSocket channel.

## How to Test

1. Open your browser and navigate to the frontend: `http://localhost:5173`.
2. Click **Create a Room** (you will automatically become the Admin).
3. Copy the URL or use the **Share Link** button.
4. Open an **Incognito Window** (or a different browser) and paste the link to join as a viewer.
5. As the Admin, play, pause, or seek the video. Watch as the Incognito window instantly synchronizes!
6. Use the chat sidebar in both windows to communicate in real-time.

> [!NOTE]
> The video source is currently mocked using an open-source Big Buck Bunny video as discussed. The architecture is perfectly set up to swap this out with Google Drive API endpoints in the future!
