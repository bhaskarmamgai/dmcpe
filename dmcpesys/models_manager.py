from django.db import models


class StatsDailyManager(models.Manager):
    def create_or_update_stats_daily(self, date, **kwargs):
        default_dict_obj = dict()
        if 'requirements_status_update_count' in kwargs:
            default_dict_obj['requirements_status_update_count'] = kwargs.get('requirements_status_update_count')
        if 'requirements_match_count' in kwargs:
            default_dict_obj['requirements_match_count'] = kwargs.get('requirements_match_count')
        stats, created = self.get_or_create(
            date=date,
            defaults=default_dict_obj
        )
        update_flag = False
        if not created and 'requirements_status_update_count' in kwargs and stats.requirements_status_update_count != kwargs.get(
                'requirements_status_update_count'):
            update_flag = True
            stats.requirements_status_update_count = kwargs.get('requirements_status_update_count')
        if not created and 'requirements_match_count' in kwargs and stats.requirements_match_count != kwargs.get(
                'requirements_match_count'):
            update_flag = True
            stats.requirements_match_count = kwargs.get('requirements_match_count')
        if update_flag:
            stats.save()
        return stats
