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

from django.views.generic import TemplateView
from django.conf.urls import patterns, url
import monitor.views

urlpatterns = [

    url(r'^$', monitor.views.monitor_home, name='monitor-home'),

    url(r'^processing/process_sounds/$', monitor.views.process_sounds,
        name='monitor-processing-process'),
    url(r'^stats/$', TemplateView.as_view(template_name='monitor/stats.html'),
        name='monitor-stats'),
    url(r'^ajax_stats/$', monitor.views.stats_ajax,
        name='monitor-stats-ajax'),

]
