import traceback

import geocoder

from carbontracker import loggerutil
from carbontracker import exceptions
from carbontracker.emissions.intensity.fetchers import co2signal
from carbontracker.emissions.intensity.fetchers import carbonintensitygb
from carbontracker.emissions.intensity.fetchers import energidataservice

# https://www.eea.europa.eu/data-and-maps/data/co2-intensity-of-electricity-generation
EU_28_2017_CARBON_INTENSITY = 294.2060978


class CarbonIntensity:
    def __init__(self,
                 carbon_intensity=None,
                 g_location=None,
                 message=None,
                 success=False,
                 is_prediction=False,
                 default=False):
        self.carbon_intensity = carbon_intensity
        self.g_location = g_location
        self.message = message
        self.success = success
        self.is_prediction = is_prediction
        if default:
            self._set_as_default()

    def _set_as_default(self):
        self.carbon_intensity = EU_28_2017_CARBON_INTENSITY
        self.g_location = None
        self.message = (
            "Live carbon intensity could not be fetched for your location. "
            "Defaulted to average carbon intensity for EU-28 in 2017 of "
            f"{EU_28_2017_CARBON_INTENSITY:.2f} gCO2/kWh.")


def carbon_intensity(logger, time_dur=None):
    # Will iterate over and find *first* suitable() api
    fetchers = [
        energidataservice.EnergiDataService(),
        carbonintensitygb.CarbonIntensityGB(),
        co2signal.CO2Signal()
    ]

    carbon_intensity = CarbonIntensity(default=True)

    try:
        g_location = geocoder.ip("me")
        if not g_location.ok:
            raise exceptions.IPLocationError(
                "Failed to retrieve location based on IP.")
    except:
        err_str = traceback.format_exc()
        logger.info(err_str)
        return carbon_intensity

    for fetcher in fetchers:
        if not fetcher.suitable(g_location):
            continue
        try:
            carbon_intensity = fetcher.carbon_intensity(g_location, time_dur)
            set_carbon_intensity_message(carbon_intensity, time_dur)
            carbon_intensity.success = True
            break
        except:
            err_str = traceback.format_exc()
            logger.info(err_str)

    logger.info(carbon_intensity.message)
    logger.output(carbon_intensity.message, verbose_level=2)

    return carbon_intensity


def set_carbon_intensity_message(ci, time_dur):
    if ci.is_prediction:
        ci.message = ("Carbon intensity for the next "
                      f"{loggerutil.convert_to_timestring(time_dur)} is "
                      f"predicted to be {ci.carbon_intensity:.2f} gCO2/kWh")
    else:
        ci.message = (f"Current carbon intensity is {ci.carbon_intensity:.2f} "
                      "gCO2/kWh")
    ci.message += f" at detected location: {ci.g_location.address}."
