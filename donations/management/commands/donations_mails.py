#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django.contrib.auth.models import User
from django.db.models import Count
from django.core.management.base import BaseCommand
from donations.models import DonationsEmailSettings
from sounds.models import Download
from donations.models import Donation
from utils.mail import send_mail_template
import datetime
import logging
import json

logger = logging.getLogger("web")


class Command(BaseCommand):
    help = 'Send donation emails'

    def handle(self, **options):
        logger.info("Sending donation emails")

        donation_settings, _ = DonationsEmailSettings.objects.get_or_create()

        if not donation_settings.enabled:
            return

        # 0) Define some variables and do some common queries that will be reused later

        donation_timespan = datetime.datetime.now()-datetime.timedelta(  # donation_timestamp is today - X days (12 mo)
            days=donation_settings.minimum_days_since_last_donation)

        email_timespan = datetime.datetime.now() - datetime.timedelta(  # email_timestap is today - Y days (3 mo)
            days=donation_settings.minimum_days_since_last_donation_email)

        user_received_donation_email_within_email_timespan = User.objects.filter(
            profile__last_donation_email_sent__gt=email_timespan).values_list('id')
        if donation_settings.never_send_email_to_uploaders:
            uploaders = User.objects.filter(profile__num_sounds__gt=0).values_list('id')
        else:
            uploaders = []
        donors_within_donation_timespan = Donation.objects.filter(user__isnull=False, created__gt=donation_timespan)\
            .values_list('user_id', flat=True)

        # 1) Check users that donated in the past
        # If it's been X days since last donation, send a reminder (typically X=365 days)
        # users_to_notify -> All users that:
        #   - Made a donation before 'donation_timespan' (12 mo)
        #   - Have not made a donation after 'donation_timespan' (12 mo)
        #   - Have not received any email regarding donations during 'email_timespan' (3 mo)
        #   - Users that have donations_reminder_email_sent set to False (they have not been sent any
        #     reminder in the past)

        users_to_notify = User.objects.filter(
            donation__created__lte=donation_timespan, profile__donations_reminder_email_sent=False)\
            .exclude(id__in=user_received_donation_email_within_email_timespan)\
            .exclude(id__in=uploaders)\
            .exclude(id__in=donors_within_donation_timespan)

        for user in users_to_notify.all():
            send_mail_template(
                u'Thanks for contributing to Freesound',
                'donations/email_donation_reminder.txt', {
                    'user': user,
                    }, None, user.email)
            user.profile.last_donation_email_sent = datetime.datetime.now()
            user.profile.donations_reminder_email_sent = True
            user.profile.save()
            logger.info("Sent donation email (%s)" % json.dumps(
                {'user_id': user.id, 'donation_email_type': 'reminder'}))

        # 2) Send email to users that download a lot of sounds without donating
        # potential_users -> All users that:
        #   - Downloaded more than M sounds during 'email_timespan' (3 months)
        #   - Have not donated during 'donation_timespan' (12 months)
        #   - Have not received any email regarding donations during 'email_timespan' (3 months)
        potential_users = Download.objects.filter(created__gte=email_timespan)\
            .exclude(user_id__in=user_received_donation_email_within_email_timespan)\
            .exclude(user_id__in=donors_within_donation_timespan) \
            .exclude(user_id__in=uploaders) \
            .values('user_id').annotate(num_download=Count('user_id')).order_by('num_download')

        for user_dict in potential_users.all():

            if user_dict['num_download'] > donation_settings.downloads_in_period:
                user = User.objects.get(id=user_dict['user_id'])

                # Check if user downloaded more than M sounds during the relevant period
                # relevant period is time since last donation + donation_timespan or email_timespan (3 mo)
                # (the take the closer one)

                send_email = False
                last_donation = Donation.objects.filter(user=user, created__gt=donation_timespan).order_by('-created')
                if last_donation.count() == 0:
                    send_email = True
                else:
                    relevant_period = max(
                        last_donation.created + datetime.timedelta(days=donation_settings.minimum_days_since_last_donation),
                        email_timespan
                    )
                    user_downloads = Download.objects.filter(created__gte=relevant_period, user=user).count()

                    if user_downloads > donation_settings.downloads_in_period:
                        send_email = True

                if send_email:
                    send_mail_template(
                        u'Have you considered making a donation?',
                        'donations/email_donation_request.txt', {
                            'user': user,
                            }, None, user.email)
                    user.profile.last_donation_email_sent = datetime.datetime.now()
                    user.profile.save()
                    logger.info("Sent donation email (%s)" % json.dumps(
                        {'user_id': user.id, 'donation_email_type': 'request'}))

        logger.info("Finished sending donation emails")
