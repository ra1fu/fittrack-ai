from decimal import Decimal
from datetime import date

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q

from config.openapi import (
    pagination_query_parameters,
    string_path_parameter,
    uuid_path_parameter,
)
from config.openapi_examples import (
    FOOD_RECOGNITION_CONFIRM_EXAMPLES,
    FOOD_RECOGNITION_UPLOAD_RESPONSE_EXAMPLES,
    MEAL_CREATE_EXAMPLES,
)
from config.pagination import paginate_queryset
from nutrition.external_foods import (
    ExternalFoodInvalidBarcode,
    ExternalFoodInvalidData,
    ExternalFoodLookupError,
    ExternalFoodLookupTimeout,
    ExternalFoodNotFound,
    lookup_food_by_barcode,
)
from nutrition.models import (
    FoodRecognition,
    FoodRecognitionItem,
    FoodRecognitionStatus,
    FoodSource,
    Meal,
    MealItem,
    MealType,
)
from nutrition.photo_storage import (
    build_food_photo_key,
    delete_food_photo,
    save_food_photo,
)
from nutrition.providers import get_food_photo_recognition_provider, parse_request_payload
from nutrition.recognitions import (
    FoodRecognitionConfirmError,
    confirm_food_recognition,
    create_food_recognition_from_ai_response,
)
from nutrition.selectors import get_visible_foods_for_user
from nutrition.serializers import (
    ConfirmFoodRecognitionSerializer,
    CreateFoodSerializer,
    CreateFoodRecognitionSerializer,
    CreateMealItemSerializer,
    CreateMealSerializer,
    FoodListResponseSerializer,
    FoodRecognitionItemSerializer,
    FoodRecognitionItemResponseSerializer,
    FoodRecognitionListResponseSerializer,
    FoodRecognitionResponseSerializer,
    FoodRecognitionSerializer,
    FoodResponseSerializer,
    FoodSerializer,
    MealItemResponseSerializer,
    MealItemSerializer,
    MealListResponseSerializer,
    MealResponseSerializer,
    MealSerializer,
    NutritionDayResponseSerializer,
    NutritionSuccessResponseSerializer,
    UpdateFoodRecognitionItemSerializer,
    UpdateMealItemSerializer,
    UpdateMealSerializer,
    UploadFoodRecognitionPhotoSerializer,
    calculate_meal_item_totals,
    UpdateFoodSerializer,
    FoodQuerySerializer,
)
from profiles.models import UserGoal


class FoodListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FoodSerializer

    @extend_schema(
        tags=["Nutrition"],
        operation_id="foods_list",
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="barcode",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="source",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[value for value, _label in FoodSource.choices],
            ),
            OpenApiParameter(
                name="is_verified",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Page size from 1 to 100. Defaults to 50.",
            ),
            OpenApiParameter(
                name="offset",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Zero-based pagination offset. Defaults to 0.",
            ),
        ],
        responses={200: FoodListResponseSerializer},
    )
    def get(self, request):
        query_serializer = FoodQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        query = query_serializer.validated_data

        foods = get_visible_foods_for_user(request.user).order_by("name")

        search = query.get("search")
        barcode = query.get("barcode")
        source = query.get("source")
        is_verified = query.get("is_verified")

        if search:
            foods = foods.filter(name__icontains=search.strip())

        if barcode:
            foods = foods.filter(barcode=barcode.strip())

        if source:
            foods = foods.filter(source=source)

        if is_verified is not None:
            foods = foods.filter(is_verified=is_verified)

        total_count = foods.count()
        limit = query["limit"]
        offset = query["offset"]
        foods = foods[offset:offset + limit]

        serializer = FoodSerializer(foods, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": {
                    "count": len(serializer.data),
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                },
            }
        )

    @extend_schema(
        tags=["Nutrition"],
        operation_id="foods_create",
        request=CreateFoodSerializer,
        responses={201: FoodResponseSerializer},
    )
    def post(self, request):
        serializer = CreateFoodSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        food = serializer.save()

        response_serializer = FoodSerializer(food)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class FoodDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FoodSerializer

    @extend_schema(
        tags=["Nutrition"],
        operation_id="foods_retrieve",
        parameters=[
            uuid_path_parameter("food_id", "Food UUID."),
        ],
        responses={200: FoodResponseSerializer},
    )
    def get(self, request, food_id):
        food = self._get_visible_food(request, food_id)
        serializer = FoodSerializer(food)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

    @extend_schema(
        tags=["Nutrition"],
        operation_id="foods_partial_update",
        request=UpdateFoodSerializer,
        parameters=[
            uuid_path_parameter("food_id", "Food UUID."),
        ],
        responses={200: FoodResponseSerializer},
    )
    def patch(self, request, food_id):
        food = self._get_owned_food(request, food_id)
        serializer = UpdateFoodSerializer(
            food,
            data=request.data,
            context={"request": request},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        food = serializer.save()

        response_serializer = FoodSerializer(food)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Nutrition"],
        operation_id="foods_delete",
        parameters=[
            uuid_path_parameter("food_id", "Food UUID."),
        ],
        responses={200: NutritionSuccessResponseSerializer},
    )
    def delete(self, request, food_id):
        food = self._get_owned_food(request, food_id)
        food.is_active = False
        food.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_visible_food(self, request, food_id):
        visible_foods = get_visible_foods_for_user(request.user)

        try:
            return visible_foods.get(id=food_id)
        except visible_foods.model.DoesNotExist as exc:
            raise NotFound("Продукт не найден") from exc

    def _get_owned_food(self, request, food_id):
        try:
            return request.user.foods.get(
                id=food_id,
                is_active=True,
            )
        except request.user.foods.model.DoesNotExist as exc:
            raise NotFound("Продукт не найден") from exc


class FoodBarcodeLookupView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FoodSerializer

    @extend_schema(
        tags=["Nutrition"],
        operation_id="foods_barcode_lookup",
        parameters=[
            string_path_parameter("barcode", "Food barcode value."),
        ],
        responses={200: FoodResponseSerializer},
    )
    def get(self, request, barcode):
        try:
            food = lookup_food_by_barcode(barcode=barcode)
        except ExternalFoodInvalidBarcode as exc:
            raise ValidationError(
                {
                    "barcode": str(exc)
                }
            ) from exc
        except ExternalFoodNotFound as exc:
            raise NotFound(str(exc)) from exc
        except ExternalFoodInvalidData as exc:
            raise ValidationError(
                {
                    "barcode": str(exc)
                }
            ) from exc
        except ExternalFoodLookupTimeout as exc:
            raise ValidationError(
                {
                    "barcode": "Внешний каталог не ответил вовремя"
                }
            ) from exc
        except ExternalFoodLookupError as exc:
            raise ValidationError(
                {
                    "barcode": "Внешний каталог временно недоступен"
                }
            ) from exc

        serializer = FoodSerializer(food)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )


class FoodRecognitionListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FoodRecognitionSerializer

    @extend_schema(
        tags=["AI Nutrition"],
        operation_id="food_recognitions_list",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[value for value, _label in FoodRecognitionStatus.choices],
            ),
            *pagination_query_parameters(),
        ],
        responses={200: FoodRecognitionListResponseSerializer},
    )
    def get(self, request):
        recognitions = (
            request.user.food_recognitions.prefetch_related("items")
            .order_by("-created_at")
        )
        status_filter = request.query_params.get("status")

        if status_filter:
            recognitions = recognitions.filter(status=status_filter)

        recognitions, meta = paginate_queryset(recognitions, request.query_params)
        serializer = FoodRecognitionSerializer(recognitions, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": meta,
            }
        )

    @extend_schema(
        tags=["AI Nutrition"],
        operation_id="food_recognitions_create",
        request=CreateFoodRecognitionSerializer,
        responses={201: FoodRecognitionResponseSerializer},
    )
    def post(self, request):
        serializer = CreateFoodRecognitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recognition = create_food_recognition_from_ai_response(
            user=request.user,
            image_key=serializer.validated_data["image_key"],
            raw_ai_response=serializer.validated_data.get("raw_ai_response"),
        )
        response_serializer = FoodRecognitionSerializer(recognition)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class FoodRecognitionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FoodRecognitionSerializer

    @extend_schema(
        tags=["AI Nutrition"],
        operation_id="food_recognitions_retrieve",
        parameters=[
            uuid_path_parameter("recognition_id", "Food recognition UUID."),
        ],
        responses={200: FoodRecognitionResponseSerializer},
    )
    def get(self, request, recognition_id):
        recognition = self._get_user_recognition(request, recognition_id)
        serializer = FoodRecognitionSerializer(recognition)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

    def _get_user_recognition(self, request, recognition_id):
        try:
            return request.user.food_recognitions.prefetch_related("items").get(
                id=recognition_id,
            )
        except request.user.food_recognitions.model.DoesNotExist as exc:
            raise NotFound("Распознавание еды не найдено") from exc


class FoodRecognitionPhotoUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = FoodRecognitionSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_photo_upload"

    @extend_schema(
        tags=["AI Nutrition"],
        operation_id="food_recognitions_upload_photo",
        request=UploadFoodRecognitionPhotoSerializer,
        responses={201: FoodRecognitionResponseSerializer},
        examples=FOOD_RECOGNITION_UPLOAD_RESPONSE_EXAMPLES,
    )
    def post(self, request):
        serializer = UploadFoodRecognitionPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_file = serializer.validated_data["image"]
        image_key = build_food_photo_key(
            user_id=request.user.id,
            content_type=image_file.content_type,
        )
        saved_image_key = save_food_photo(
            image_file=image_file,
            image_key=image_key,
        )

        try:
            try:
                request_payload = parse_request_payload(
                    serializer.validated_data.get("raw_ai_response")
                )
            except ValueError as exc:
                raise ValidationError(
                    {
                        "raw_ai_response": "Укажите корректный JSON"
                    }
                ) from exc

            provider = get_food_photo_recognition_provider()
            raw_ai_response = provider.recognize(
                image_key=saved_image_key,
                image_file=image_file,
                request_payload=request_payload,
            )
            recognition = create_food_recognition_from_ai_response(
                user=request.user,
                image_key=saved_image_key,
                raw_ai_response=raw_ai_response,
            )
            response_serializer = FoodRecognitionSerializer(recognition)
        finally:
            delete_food_photo(image_key=saved_image_key)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class FoodRecognitionItemDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FoodRecognitionItemSerializer

    @extend_schema(
        tags=["AI Nutrition"],
        operation_id="food_recognition_items_partial_update",
        request=UpdateFoodRecognitionItemSerializer,
        parameters=[
            uuid_path_parameter(
                "recognition_item_id",
                "Food recognition item UUID.",
            ),
        ],
        responses={200: FoodRecognitionItemResponseSerializer},
    )
    def patch(self, request, recognition_item_id):
        recognition_item = self._get_user_recognition_item(request, recognition_item_id)

        if recognition_item.recognition.status != FoodRecognitionStatus.DRAFT:
            raise ValidationError(
                {
                    "status": "Можно редактировать только черновик распознавания"
                }
            )

        serializer = UpdateFoodRecognitionItemSerializer(
            recognition_item,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        recognition_item = serializer.save()

        response_serializer = FoodRecognitionItemSerializer(recognition_item)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["AI Nutrition"],
        operation_id="food_recognition_items_delete",
        parameters=[
            uuid_path_parameter(
                "recognition_item_id",
                "Food recognition item UUID.",
            ),
        ],
        responses={200: NutritionSuccessResponseSerializer},
    )
    def delete(self, request, recognition_item_id):
        recognition_item = self._get_user_recognition_item(request, recognition_item_id)

        if recognition_item.recognition.status != FoodRecognitionStatus.DRAFT:
            raise ValidationError(
                {
                    "status": "Можно удалять позиции только из черновика распознавания"
                }
            )

        recognition_item.delete()

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_user_recognition_item(self, request, recognition_item_id):
        try:
            return FoodRecognitionItem.objects.select_related("recognition").get(
                id=recognition_item_id,
                recognition__user=request.user,
            )
        except FoodRecognitionItem.DoesNotExist as exc:
            raise NotFound("Позиция распознавания еды не найдена") from exc


class FoodRecognitionConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MealSerializer

    @extend_schema(
        tags=["AI Nutrition"],
        operation_id="food_recognitions_confirm",
        request=ConfirmFoodRecognitionSerializer,
        parameters=[
            uuid_path_parameter("recognition_id", "Food recognition UUID."),
        ],
        responses={200: MealResponseSerializer},
        examples=FOOD_RECOGNITION_CONFIRM_EXAMPLES,
    )
    def post(self, request, recognition_id):
        recognition = self._get_user_recognition(request, recognition_id)
        serializer = ConfirmFoodRecognitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            meal = confirm_food_recognition(
                recognition=recognition,
                meal_data=serializer.validated_data,
            )
        except FoodRecognitionConfirmError as exc:
            raise ValidationError(
                {
                    "recognition": str(exc)
                }
            ) from exc

        response_serializer = MealSerializer(meal)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_user_recognition(self, request, recognition_id):
        try:
            return FoodRecognition.objects.prefetch_related("items").get(
                id=recognition_id,
                user=request.user,
            )
        except FoodRecognition.DoesNotExist as exc:
            raise NotFound("Распознавание еды не найдено") from exc


class MealListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MealSerializer

    @extend_schema(
        tags=["Nutrition"],
        operation_id="meals_list",
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Meal date in YYYY-MM-DD format.",
            ),
            OpenApiParameter(
                name="meal_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[value for value, _label in MealType.choices],
            ),
            *pagination_query_parameters(),
        ],
        responses={200: MealListResponseSerializer},
    )
    def get(self, request):
        meals = request.user.meals.prefetch_related("items").order_by(
            "-meal_date",
            "eaten_at",
            "created_at",
        )
        meal_date = request.query_params.get("date")
        meal_type = request.query_params.get("meal_type")

        if meal_date:
            meals = meals.filter(meal_date=meal_date)

        if meal_type:
            meals = meals.filter(meal_type=meal_type)

        meals, meta = paginate_queryset(meals, request.query_params)
        serializer = MealSerializer(meals, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": meta,
            }
        )

    @extend_schema(
        tags=["Nutrition"],
        operation_id="meals_create",
        request=CreateMealSerializer,
        responses={201: MealResponseSerializer},
        examples=MEAL_CREATE_EXAMPLES,
    )
    def post(self, request):
        serializer = CreateMealSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        meal = serializer.save()

        response_serializer = MealSerializer(meal)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )


class MealDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MealSerializer

    @extend_schema(
        tags=["Nutrition"],
        operation_id="meals_retrieve",
        parameters=[
            uuid_path_parameter("meal_id", "Meal UUID."),
        ],
        responses={200: MealResponseSerializer},
    )
    def get(self, request, meal_id):
        meal = self._get_user_meal(request, meal_id)
        serializer = MealSerializer(meal)

        return Response(
            {
                "data": serializer.data,
                "meta": {},
            }
        )

    @extend_schema(
        tags=["Nutrition"],
        operation_id="meals_partial_update",
        request=UpdateMealSerializer,
        parameters=[
            uuid_path_parameter("meal_id", "Meal UUID."),
        ],
        responses={200: MealResponseSerializer},
    )
    def patch(self, request, meal_id):
        meal = self._get_user_meal(request, meal_id)
        serializer = UpdateMealSerializer(
            meal,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        meal = serializer.save()

        response_serializer = MealSerializer(meal)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Nutrition"],
        operation_id="meals_delete",
        parameters=[
            uuid_path_parameter("meal_id", "Meal UUID."),
        ],
        responses={200: NutritionSuccessResponseSerializer},
    )
    def delete(self, request, meal_id):
        meal = self._get_user_meal(request, meal_id)
        meal.delete()

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_user_meal(self, request, meal_id):
        try:
            return request.user.meals.prefetch_related("items").get(id=meal_id)
        except request.user.meals.model.DoesNotExist as exc:
            raise NotFound("Приём пищи не найден") from exc


class MealItemCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MealItemSerializer

    @extend_schema(
        tags=["Nutrition"],
        operation_id="meal_items_create",
        request=CreateMealItemSerializer,
        parameters=[
            uuid_path_parameter("meal_id", "Parent meal UUID."),
        ],
        responses={201: MealItemResponseSerializer},
    )
    def post(self, request, meal_id):
        meal = self._get_user_meal(request, meal_id)
        serializer = CreateMealItemSerializer(
            data=request.data,
            context={
                "request": request,
                "meal": meal,
            },
        )
        serializer.is_valid(raise_exception=True)
        meal_item = serializer.save()

        response_serializer = MealItemSerializer(meal_item)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_user_meal(self, request, meal_id):
        try:
            return Meal.objects.get(id=meal_id, user=request.user)
        except Meal.DoesNotExist as exc:
            raise NotFound("Приём пищи не найден") from exc


class MealItemDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MealItemSerializer

    @extend_schema(
        tags=["Nutrition"],
        operation_id="meal_items_partial_update",
        request=UpdateMealItemSerializer,
        parameters=[
            uuid_path_parameter("meal_item_id", "Meal item UUID."),
        ],
        responses={200: MealItemResponseSerializer},
    )
    def patch(self, request, meal_item_id):
        meal_item = self._get_user_meal_item(request, meal_item_id)
        serializer = UpdateMealItemSerializer(
            meal_item,
            data=request.data,
            context={
                "request": request,
                "meal_item": meal_item,
            },
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        meal_item = serializer.save()

        response_serializer = MealItemSerializer(meal_item)

        return Response(
            {
                "data": response_serializer.data,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Nutrition"],
        operation_id="meal_items_delete",
        parameters=[
            uuid_path_parameter("meal_item_id", "Meal item UUID."),
        ],
        responses={200: NutritionSuccessResponseSerializer},
    )
    def delete(self, request, meal_item_id):
        meal_item = self._get_user_meal_item(request, meal_item_id)
        meal_item.deleted_at = timezone.now()
        meal_item.server_version += 1
        meal_item.save(update_fields=["deleted_at", "server_version", "updated_at"])

        return Response(
            {
                "data": {
                    "success": True,
                },
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    def _get_user_meal_item(self, request, meal_item_id):
        try:
            return MealItem.objects.select_related("meal", "food").get(
                id=meal_item_id,
                meal__user=request.user,
                deleted_at__isnull=True,
            )
        except MealItem.DoesNotExist as exc:
            raise NotFound("Продукт в приёме пищи не найден") from exc


class NutritionDayView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MealSerializer

    @extend_schema(
        tags=["Nutrition"],
        operation_id="nutrition_day_retrieve",
        parameters=[
            OpenApiParameter(
                name="meal_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                required=True,
                description="Meal day in YYYY-MM-DD format.",
            ),
        ],
        responses={200: NutritionDayResponseSerializer},
    )
    def get(self, request, meal_date):
        parsed_meal_date = _parse_meal_date(meal_date)
        meals = (
            request.user.meals.filter(meal_date=parsed_meal_date)
            .prefetch_related("items")
            .order_by("eaten_at", "created_at")
        )
        serializer = MealSerializer(meals, many=True)
        totals = _calculate_day_totals(meals)
        target_summary = _build_day_target_summary(request.user, parsed_meal_date, totals)

        return Response(
            {
                "data": {
                    "date": meal_date,
                    "totals": totals,
                    "targets": target_summary["targets"],
                    "progress": target_summary["progress"],
                    "meals": serializer.data,
                },
                "meta": {},
            }
        )


def _parse_meal_date(meal_date: str) -> date:
    try:
        return date.fromisoformat(meal_date)
    except ValueError as exc:
        raise ValidationError(
            {
                "meal_date": "Укажите дату в формате YYYY-MM-DD"
            }
        ) from exc


def _calculate_day_totals(meals):
    totals = {
        "calories": Decimal("0.00"),
        "protein": Decimal("0.00"),
        "fat": Decimal("0.00"),
        "carbs": Decimal("0.00"),
    }

    for meal in meals:
        meal_totals = calculate_meal_item_totals(
            meal.items.filter(deleted_at__isnull=True)
        )
        totals["calories"] += Decimal(meal_totals["calories"])
        totals["protein"] += Decimal(meal_totals["protein"])
        totals["fat"] += Decimal(meal_totals["fat"])
        totals["carbs"] += Decimal(meal_totals["carbs"])

    return {
        key: f"{value:.2f}"
        for key, value in totals.items()
    }


def _build_day_target_summary(user, meal_date: date, totals: dict) -> dict:
    active_goal = _get_active_nutrition_goal(user, meal_date)
    targets = _serialize_goal_targets(active_goal)

    return {
        "targets": targets,
        "progress": {
            "calories": _build_progress_item(totals["calories"], targets["calories"]),
            "protein": _build_progress_item(totals["protein"], targets["protein"]),
            "fat": _build_progress_item(totals["fat"], targets["fat"]),
            "carbs": _build_progress_item(totals["carbs"], targets["carbs"]),
        },
    }


def _get_active_nutrition_goal(user, meal_date: date):
    return (
        UserGoal.objects.filter(
            user=user,
            active_from__lte=meal_date,
        )
        .filter(
            Q(active_to__isnull=True) | Q(active_to__gte=meal_date),
        )
        .order_by("-active_from", "-created_at")
        .first()
    )


def _serialize_goal_targets(goal) -> dict:
    if goal is None:
        return {
            "active_goal_id": None,
            "goal_type": None,
            "calories": None,
            "protein": None,
            "fat": None,
            "carbs": None,
        }

    return {
        "active_goal_id": str(goal.id),
        "goal_type": goal.goal_type,
        "calories": _format_decimal(goal.calorie_target),
        "protein": _format_decimal(goal.protein_target_g),
        "fat": _format_decimal(goal.fat_target_g),
        "carbs": _format_decimal(goal.carbs_target_g),
    }


def _build_progress_item(consumed_value: str, target_value: str | None) -> dict:
    consumed = Decimal(consumed_value)

    if target_value is None:
        return {
            "consumed": f"{consumed:.2f}",
            "target": None,
            "remaining": None,
            "percent": None,
        }

    target = Decimal(target_value)
    remaining = target - consumed
    percent = Decimal("0.00")

    if target > 0:
        percent = (consumed / target * Decimal("100")).quantize(Decimal("0.01"))

    return {
        "consumed": f"{consumed:.2f}",
        "target": f"{target:.2f}",
        "remaining": f"{remaining:.2f}",
        "percent": f"{percent:.2f}",
    }


def _format_decimal(value) -> str | None:
    if value is None:
        return None

    return f"{Decimal(value):.2f}"
