from rest_framework.routers import DefaultRouter

from .views import ResourceCategoryViewSet

app_name = "categories"


router = DefaultRouter()

router.register("", ResourceCategoryViewSet, basename="category")


urlpatterns = router.urls
