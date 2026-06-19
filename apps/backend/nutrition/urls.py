from django.urls import path

from nutrition.views import (
    FoodBarcodeLookupView,
    FoodListCreateView,
    FoodRecognitionConfirmView,
    FoodRecognitionDetailView,
    FoodRecognitionItemDetailView,
    FoodRecognitionListCreateView,
    FoodRecognitionPhotoUploadView,
    MealItemCreateView,
    MealItemDetailView,
    MealDetailView,
    MealListCreateView,
    NutritionDayView,
    FoodDetailView,
)

urlpatterns = [
    path("nutrition/days/<str:meal_date>", NutritionDayView.as_view(), name="nutrition-day"),
    path(
        "nutrition/photo-recognitions",
        FoodRecognitionListCreateView.as_view(),
        name="food-recognitions",
    ),
    path(
        "nutrition/photo-recognitions/upload",
        FoodRecognitionPhotoUploadView.as_view(),
        name="food-recognition-photo-upload",
    ),
    path(
        "nutrition/photo-recognitions/<uuid:recognition_id>",
        FoodRecognitionDetailView.as_view(),
        name="food-recognition-detail",
    ),
    path(
        "nutrition/photo-recognitions/<uuid:recognition_id>/confirm",
        FoodRecognitionConfirmView.as_view(),
        name="food-recognition-confirm",
    ),
    path(
        "nutrition/photo-recognition-items/<uuid:recognition_item_id>",
        FoodRecognitionItemDetailView.as_view(),
        name="food-recognition-item-detail",
    ),
    path("foods", FoodListCreateView.as_view(), name="foods"),
    path(
        "foods/barcodes/<str:barcode>/lookup",
        FoodBarcodeLookupView.as_view(),
        name="food-barcode-lookup",
    ),
    path("foods/<uuid:food_id>", FoodDetailView.as_view(), name="food-detail"),
    path("meals", MealListCreateView.as_view(), name="meals"),
    path("meals/<uuid:meal_id>", MealDetailView.as_view(), name="meal-detail"),
    path("meals/<uuid:meal_id>/items", MealItemCreateView.as_view(), name="meal-items"),
    path("meal-items/<uuid:meal_item_id>", MealItemDetailView.as_view(), name="meal-item-detail"),
]
