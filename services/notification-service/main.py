"""
Notification Service for AI Planner
Handles email, SMS, and webhook notifications
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional, Any
from datetime import datetime
import redis
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis for notification queue
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

app = FastAPI(
    title="AI Planner Notification Service",
    description="Handles notifications for AI Planner system",
    version="1.0.0"
)

class EmailNotification(BaseModel):
    to: EmailStr
    subject: str
    body: str
    html_body: Optional[str] = None
    priority: str = "normal"  # low, normal, high
    
class SMSNotification(BaseModel):
    phone_number: str
    message: str
    priority: str = "normal"

class WebhookNotification(BaseModel):
    url: str
    payload: Dict[str, Any]
    headers: Optional[Dict[str, str]] = {}
    method: str = "POST"

class NotificationStatus(BaseModel):
    id: str
    type: str
    status: str  # pending, sent, failed
    created_at: datetime
    sent_at: Optional[datetime] = None
    error: Optional[str] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "notification-service", "timestamp": datetime.utcnow()}

async def send_email_notification(notification: EmailNotification, notification_id: str):
    """Send email notification"""
    try:
        # In a real implementation, you'd use a proper email service
        # For demo purposes, we'll just log the email
        logger.info(f"Sending email to {notification.to}: {notification.subject}")
        
        # Simulate email sending
        import time
        time.sleep(1)  # Simulate network delay
        
        # Update status to sent
        update_notification_status(notification_id, "sent", sent_at=datetime.utcnow())
        
    except Exception as e:
        logger.error(f"Failed to send email {notification_id}: {e}")
        update_notification_status(notification_id, "failed", error=str(e))

async def send_sms_notification(notification: SMSNotification, notification_id: str):
    """Send SMS notification"""
    try:
        # In a real implementation, you'd use an SMS service like Twilio
        logger.info(f"Sending SMS to {notification.phone_number}: {notification.message}")
        
        # Simulate SMS sending
        import time
        time.sleep(0.5)
        
        # Update status to sent
        update_notification_status(notification_id, "sent", sent_at=datetime.utcnow())
        
    except Exception as e:
        logger.error(f"Failed to send SMS {notification_id}: {e}")
        update_notification_status(notification_id, "failed", error=str(e))

async def send_webhook_notification(notification: WebhookNotification, notification_id: str):
    """Send webhook notification"""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=notification.method,
                url=notification.url,
                json=notification.payload,
                headers=notification.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status >= 400:
                    raise Exception(f"Webhook returned status {response.status}")
                
                logger.info(f"Webhook sent to {notification.url}: {response.status}")
                update_notification_status(notification_id, "sent", sent_at=datetime.utcnow())
        
    except Exception as e:
        logger.error(f"Failed to send webhook {notification_id}: {e}")
        update_notification_status(notification_id, "failed", error=str(e))

def create_notification_status(notification_type: str) -> str:
    """Create a new notification status record"""
    notification_id = f"notif_{int(datetime.utcnow().timestamp())}_{hash(str(datetime.utcnow()))}"
    
    status = NotificationStatus(
        id=notification_id,
        type=notification_type,
        status="pending",
        created_at=datetime.utcnow()
    )
    
    redis_client.setex(
        f"notification:{notification_id}",
        86400,  # 24 hours
        json.dumps(status.dict(), default=str)
    )
    
    return notification_id

def update_notification_status(notification_id: str, status: str, **kwargs):
    """Update notification status"""
    notification_data = redis_client.get(f"notification:{notification_id}")
    if notification_data:
        notification = json.loads(notification_data)
        notification["status"] = status
        for key, value in kwargs.items():
            if value is not None:
                notification[key] = value.isoformat() if isinstance(value, datetime) else value
        
        redis_client.setex(
            f"notification:{notification_id}",
            86400,
            json.dumps(notification, default=str)
        )

@app.post("/notifications/email")
async def send_email(notification: EmailNotification, background_tasks: BackgroundTasks):
    """Send email notification"""
    notification_id = create_notification_status("email")
    
    # Add to background task queue
    background_tasks.add_task(send_email_notification, notification, notification_id)
    
    return {"message": "Email notification queued", "notification_id": notification_id}

@app.post("/notifications/sms")
async def send_sms(notification: SMSNotification, background_tasks: BackgroundTasks):
    """Send SMS notification"""
    notification_id = create_notification_status("sms")
    
    # Add to background task queue
    background_tasks.add_task(send_sms_notification, notification, notification_id)
    
    return {"message": "SMS notification queued", "notification_id": notification_id}

@app.post("/notifications/webhook")
async def send_webhook(notification: WebhookNotification, background_tasks: BackgroundTasks):
    """Send webhook notification"""
    notification_id = create_notification_status("webhook")
    
    # Add to background task queue
    background_tasks.add_task(send_webhook_notification, notification, notification_id)
    
    return {"message": "Webhook notification queued", "notification_id": notification_id}

@app.get("/notifications/{notification_id}/status", response_model=NotificationStatus)
async def get_notification_status(notification_id: str):
    """Get notification status"""
    notification_data = redis_client.get(f"notification:{notification_id}")
    
    if not notification_data:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return json.loads(notification_data)

@app.get("/notifications/stats")
async def get_notification_stats():
    """Get notification statistics"""
    stats = {
        "total": 0,
        "pending": 0,
        "sent": 0,
        "failed": 0,
        "by_type": {}
    }
    
    for key in redis_client.scan_iter(match="notification:*"):
        notification_data = redis_client.get(key)
        if notification_data:
            notification = json.loads(notification_data)
            stats["total"] += 1
            stats[notification["status"]] = stats.get(notification["status"], 0) + 1
            
            notification_type = notification["type"]
            if notification_type not in stats["by_type"]:
                stats["by_type"][notification_type] = {"total": 0, "pending": 0, "sent": 0, "failed": 0}
            
            stats["by_type"][notification_type]["total"] += 1
            stats["by_type"][notification_type][notification["status"]] += 1
    
    return stats

@app.post("/notifications/itinerary-ready")
async def notify_itinerary_ready(
    background_tasks: BackgroundTasks,
    city: str,
    user_email: Optional[EmailStr] = None,
    webhook_url: Optional[str] = None
):
    """Send notification when itinerary is ready"""
    notifications_sent = []
    
    # Send email notification if email provided
    if user_email:
        email_notification = EmailNotification(
            to=user_email,
            subject=f"Your {city} Travel Itinerary is Ready! ✈️",
            body=f"Great news! Your personalized travel itinerary for {city} has been generated and is ready for you to review.",
            html_body=f"""
            <h2>Your {city} Travel Itinerary is Ready! ✈️</h2>
            <p>Great news! Your personalized travel itinerary for <strong>{city}</strong> has been generated.</p>
            <p>You can now view and download your itinerary from the AI Planner dashboard.</p>
            <p>Happy travels!</p>
            <p><em>The AI Planner Team</em></p>
            """,
            priority="high"
        )
        
        notification_id = create_notification_status("email")
        background_tasks.add_task(send_email_notification, email_notification, notification_id)
        notifications_sent.append({"type": "email", "id": notification_id})
    
    # Send webhook notification if URL provided
    if webhook_url:
        webhook_notification = WebhookNotification(
            url=webhook_url,
            payload={
                "event": "itinerary_ready",
                "city": city,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Itinerary for {city} is ready"
            }
        )
        
        notification_id = create_notification_status("webhook")
        background_tasks.add_task(send_webhook_notification, webhook_notification, notification_id)
        notifications_sent.append({"type": "webhook", "id": notification_id})
    
    return {
        "message": "Itinerary ready notifications queued",
        "city": city,
        "notifications": notifications_sent
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
