# Eureka Registrar Buildpack

This is a intermediate buildpack for Cloud Foundry that provides integration with the Spring Cloud Eureka 
server *for any programming language* supported by the platform, and requiring *zero application code 
changes*.

When this buildpack is present in your Cloud Foundry deployment, all you will have to do to register all 
instances of your application with the Eureka discovery server is bind the application to your Spring Cloud
Eureka Servive instance. Instances will then automatically be registered and continue to send heartbeats
as long as the application container is alive when you provide the eureka_registrary_sidecar as an intermediate
buildpack when pushing your application.

```sh
foo@bar:my-app$ cf push my-app --no-start
foo@bar:my-app$ cf v3-push my-app -p <path/to/bundle> -b eureka_registrary_sidecar -b <final_buildpack>

```

See https://docs.cloudfoundry.org/buildpacks/understand-buildpacks.html for buildpack basics. This is an 
intermediate buildpack using only the bin/supply script.

See https://docs.cloudfoundry.org/buildpacks/use-multiple-buildpacks.html#Specifying%20Buildpacks%20with%20the%20cf%20CLI
for information about pushing an application with multiple buildpacks.