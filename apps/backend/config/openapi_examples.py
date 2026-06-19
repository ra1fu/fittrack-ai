from drf_spectacular.utils import OpenApiExample


AUTH_REGISTER_EXAMPLES = [
    OpenApiExample(
        "Register request",
        value={
            "email": "user@example.com",
            "password": "strong-password-123",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
        request_only=True,
    ),
    OpenApiExample(
        "Register response",
        value={
            "data": {
                "id": "00000000-0000-4000-8000-000000000001",
                "email": "user@example.com",
                "email_verified": False,
            },
            "meta": {},
        },
        response_only=True,
        status_codes=["201"],
    ),
]


AUTH_LOGIN_EXAMPLES = [
    OpenApiExample(
        "Login request",
        value={
            "email": "user@example.com",
            "password": "strong-password-123",
        },
        request_only=True,
    ),
    OpenApiExample(
        "Login response",
        value={
            "data": {
                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
                "user": {
                    "id": "00000000-0000-4000-8000-000000000001",
                    "email": "user@example.com",
                    "email_verified": False,
                },
            },
            "meta": {},
        },
        response_only=True,
        status_codes=["200"],
    ),
]


AUTH_REFRESH_EXAMPLES = [
    OpenApiExample(
        "Refresh request",
        value={
            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
        },
        request_only=True,
    ),
    OpenApiExample(
        "Refresh response",
        value={
            "data": {
                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh2",
            },
            "meta": {},
        },
        response_only=True,
        status_codes=["200"],
    ),
]


AUTH_LOGOUT_EXAMPLES = [
    OpenApiExample(
        "Logout request",
        value={
            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
        },
        request_only=True,
    ),
    OpenApiExample(
        "Logout response",
        value={
            "data": {
                "success": True,
            },
            "meta": {},
        },
        response_only=True,
        status_codes=["200"],
    ),
]


MEAL_CREATE_EXAMPLES = [
    OpenApiExample(
        "Create meal request",
        value={
            "meal_date": "2026-06-19",
            "meal_type": "breakfast",
            "custom_name": "",
            "notes": "After morning workout",
            "local_device_id": "00000000-0000-4000-8000-000000000010",
            "client_updated_at": "2026-06-19T09:00:00Z",
        },
        request_only=True,
    ),
    OpenApiExample(
        "Create meal response",
        value={
            "data": {
                "id": "00000000-0000-4000-8000-000000000011",
                "meal_date": "2026-06-19",
                "meal_type": "breakfast",
                "custom_name": "",
                "eaten_at": None,
                "notes": "After morning workout",
                "local_device_id": "00000000-0000-4000-8000-000000000010",
                "client_updated_at": "2026-06-19T09:00:00Z",
                "server_version": 1,
                "items": [],
                "totals": {
                    "calories": "0.00",
                    "protein": "0.00",
                    "fat": "0.00",
                    "carbs": "0.00",
                },
            },
            "meta": {},
        },
        response_only=True,
        status_codes=["201"],
    ),
]


FOOD_RECOGNITION_CONFIRM_EXAMPLES = [
    OpenApiExample(
        "Confirm recognition request",
        value={
            "meal_date": "2026-06-19",
            "meal_type": "lunch",
            "custom_name": "",
            "notes": "AI photo recognition",
        },
        request_only=True,
    ),
]


FOOD_RECOGNITION_UPLOAD_RESPONSE_EXAMPLES = [
    OpenApiExample(
        "Upload photo response",
        value={
            "data": {
                "id": "00000000-0000-4000-8000-000000000020",
                "image_key": "nutrition/photo-recognitions/user/photo.jpg",
                "status": "draft",
                "raw_ai_response": {
                    "items": [
                        {
                            "name": "Rice",
                            "weight_g": 180,
                            "calories_per_100g": 130,
                            "protein_per_100g": 2.7,
                            "fat_per_100g": 0.3,
                            "carbs_per_100g": 28,
                            "confidence": 0.92,
                        }
                    ]
                },
                "error_code": "",
                "error_message": "",
                "confirmed_meal_id": None,
                "confirmed_at": None,
                "items": [
                    {
                        "id": "00000000-0000-4000-8000-000000000021",
                        "position": 1,
                        "ai_name": "Rice",
                        "ai_confidence": "0.9200",
                        "ai_weight_g": "180.00",
                        "ai_calories_per_100g": "130.00",
                        "ai_protein_per_100g": "2.70",
                        "ai_fat_per_100g": "0.30",
                        "ai_carbs_per_100g": "28.00",
                        "corrected_name": "Rice",
                        "corrected_weight_g": "180.00",
                        "corrected_calories_per_100g": "130.00",
                        "corrected_protein_per_100g": "2.70",
                        "corrected_fat_per_100g": "0.30",
                        "corrected_carbs_per_100g": "28.00",
                        "user_corrected": False,
                        "totals": {
                            "calories": "234.00",
                            "protein": "4.86",
                            "fat": "0.54",
                            "carbs": "50.40",
                        },
                        "created_at": "2026-06-19T09:00:00Z",
                        "updated_at": "2026-06-19T09:00:00Z",
                    }
                ],
                "created_at": "2026-06-19T09:00:00Z",
                "updated_at": "2026-06-19T09:00:00Z",
            },
            "meta": {},
        },
        response_only=True,
        status_codes=["201"],
    ),
]


WORKOUT_CREATE_EXAMPLES = [
    OpenApiExample(
        "Start workout request",
        value={
            "name": "Push day",
            "started_at": "2026-06-19T10:00:00Z",
            "notes": "Chest and shoulders",
            "local_device_id": "00000000-0000-4000-8000-000000000030",
            "client_updated_at": "2026-06-19T10:00:05Z",
        },
        request_only=True,
    ),
    OpenApiExample(
        "Start workout response",
        value={
            "data": {
                "id": "00000000-0000-4000-8000-000000000031",
                "source_routine_id": None,
                "source_routine_day_id": None,
                "name": "Push day",
                "status": "active",
                "started_at": "2026-06-19T10:00:00Z",
                "finished_at": None,
                "duration_seconds": None,
                "notes": "Chest and shoulders",
                "local_device_id": "00000000-0000-4000-8000-000000000030",
                "client_updated_at": "2026-06-19T10:00:05Z",
                "server_version": 1,
                "metrics": {
                    "total_volume": "0.00",
                    "completed_working_sets": 0,
                    "completed_sets": 0,
                },
                "exercises": [],
                "created_at": "2026-06-19T10:00:05Z",
                "updated_at": "2026-06-19T10:00:05Z",
            },
            "meta": {},
        },
        response_only=True,
        status_codes=["201"],
    ),
]


DASHBOARD_SUMMARY_EXAMPLES = [
    OpenApiExample(
        "Dashboard summary response",
        value={
            "data": {
                "date": "2026-06-19",
                "nutrition": {
                    "totals": {
                        "calories": "234.00",
                        "protein": "4.86",
                        "fat": "0.54",
                        "carbs": "50.40",
                    },
                    "targets": {
                        "active_goal_id": "00000000-0000-4000-8000-000000000040",
                        "goal_type": "muscle_gain",
                        "calories": "2400.00",
                        "protein": "160.00",
                        "fat": "70.00",
                        "carbs": "300.00",
                    },
                    "progress": {
                        "calories": {
                            "consumed": "234.00",
                            "target": "2400.00",
                            "remaining": "2166.00",
                            "percent": "9.75",
                        },
                        "protein": {
                            "consumed": "4.86",
                            "target": "160.00",
                            "remaining": "155.14",
                            "percent": "3.04",
                        },
                        "fat": {
                            "consumed": "0.54",
                            "target": "70.00",
                            "remaining": "69.46",
                            "percent": "0.77",
                        },
                        "carbs": {
                            "consumed": "50.40",
                            "target": "300.00",
                            "remaining": "249.60",
                            "percent": "16.80",
                        },
                    },
                    "meal_count": 1,
                },
                "workouts": {
                    "week_start": "2026-06-15",
                    "week_end": "2026-06-21",
                    "completed_workouts": 1,
                    "total_volume": "2500.00",
                    "completed_working_sets": 8,
                    "duration_seconds": 3600,
                },
            },
            "meta": {},
        },
        response_only=True,
        status_codes=["200"],
    ),
]
