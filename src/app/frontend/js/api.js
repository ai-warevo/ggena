const MODULE_NAME = 'image';

export function connect(onMessage, onOpen, onClose, onError) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/generate/${MODULE_NAME}`;
    console.log(`[Frontend] Attempting to connect to WebSocket: ${wsUrl}`);
    
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('[Frontend] WebSocket connection opened successfully');
        if (onOpen) onOpen();
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('[Frontend] Received message from server:', data);
            if (onMessage) onMessage(data);
        } catch (err) {
            console.error('[Frontend] Failed to parse WebSocket message:', err);
        }
    };

    socket.onclose = (event) => {
        console.warn(`[Frontend] WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}`);
        if (onClose) onClose(event);
    };

    socket.onerror = (error) => {
        console.error('[Frontend] WebSocket error occurred:', error);
        if (onError) onError(error);
        socket.close();
    };

    return socket;
}
